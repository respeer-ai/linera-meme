<template>
  <div :style='{ height: height }'>
    <chart-toolbar
      v-model='toolbarConfig'
      :token0='token0App'
      :token1='token1App'
    />
    <chart-view
      style='width: 100%;'
      :data='klinePoints'
      :chart-type='toolbarConfig.chartType'
      :indicator-config='toolbarConfig.indicatorConfig'
      :background-history-status='backgroundHistoryStatus'
      @load-new-data='onLoadNewData'
      @load-old-data='onLoadOldData'
      @indicators-ready='onIndicatorsReady'
      :height='chartHeight'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch, onBeforeMount, toRef, nextTick } from 'vue'
import { kline, swap, ams } from 'src/stores/export'
import { dbKline } from 'src/controller'
// import { useRouter } from 'vue-router'
import { klineWorker } from 'src/worker'
import { KLineData } from './chart/KlineData'

import ChartView from './chart/ChartView.vue'
import ChartToolbar from './ChartToolbar.vue'
import { ChartType } from './ChartType'
import type { IndicatorConfig } from './IndicatorSelector.vue'
import { getFirstScreenFetchWindowSize, resolveBackgroundHistoryStatus, resolveFetchSortDecision, resolveLoadRange, resolveNextFetchTimestamp, resolveStartupRequestPlan, shouldDeferHistoryLoadUntilFirstPaint, shouldRestartKlineOnSelectedPoolChange, shouldScheduleBackgroundHistoryBackfill, SortReason, type Reason } from './priceChartStartup'
import { createStartupInstrumentation } from './startupInstrumentation'
import { createStartupBaselineRecorder, installStartupBaselineDebug } from './startupBaseline'
import { dequeueLoadDirection, enqueueLoadDirection, type LoadDirection } from './loadQueue'

const STORAGE_KEY = 'kline_chart_settings'

const props = defineProps({
  height: { type: String, default: '550px' }
})
const height = toRef(props, 'height')

// 默认配置
const defaultToolbarConfig = {
  interval: kline.Interval.FIVE_MINUTE,
  chartType: ChartType.CANDLESTICK,
  indicatorConfig: {
    ma: { enabled: { ma5: true, ma10: true, ma30: true } },
    ema: { enabled: { ema7: false, ema25: false } },
    boll: false,
    volume: true,
    showVolume: true,
    showGrid: true,
    showCrosshair: true
  } as IndicatorConfig
}

// 从localStorage读取保存的设置
const loadSettings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return { ...defaultToolbarConfig, ...parsed }
    }
  } catch (e) {
    console.error('Failed to load chart settings:', e)
  }
  return defaultToolbarConfig
}

// 保存设置到localStorage
const saveSettings = (config: typeof toolbarConfig.value) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch (e) {
    console.error('Failed to save chart settings:', e)
  }
}

// 计算图表高度（总高度 - 工具栏高度）
const chartHeight = computed(() => {
  const totalHeight = parseInt(height.value)
  const toolbarHeight = 50 // 工具栏实际高度约 44-48px，留一些余量
  return `${totalHeight - toolbarHeight}px`
})

const toolbarConfig = ref(loadSettings())

// 监听设置变化，自动保存
watch(toolbarConfig, (newConfig) => {
  saveSettings(newConfig)
}, { deep: true })

const selectedInterval = computed(() => toolbarConfig.value.interval)

const getWindowSize = (interval: kline.Interval): number => getFirstScreenFetchWindowSize(interval)

// 根据时间周期获取最大数据点数（用于内存管理，不影响 IndexedDB 存储）
const getMaxPoints = (interval: kline.Interval): number => {
  switch (interval) {
    case kline.Interval.ONE_MINUTE:
      return 1800 // 30小时
    case kline.Interval.FIVE_MINUTE:
      return 720 // 60小时
    case kline.Interval.TEN_MINUTE:
      return 720 // 120小时
    case kline.Interval.FIFTEEN_MINUTE:
      return 720 // 180小时
    case kline.Interval.ONE_HOUR:
      return 720 // 30天
    case kline.Interval.FOUR_HOUR:
      return 720 // 120天
    case kline.Interval.ONE_DAY:
      return 365 // 1年
    case kline.Interval.ONE_MONTH:
      return 120 // 10年
    default:
      return 1800
  }
}

const buyToken = computed(() => swap.Swap.buyToken())
const sellToken = computed(() => swap.Swap.sellToken())
const selectedPool = computed(() => swap.Swap.selectedPool())
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000) || 0)

// 创建默认的Application对象用于显示placeholder
const defaultApp = {} as ams.Application

// Sell在前，Buy在后（与交易面板一致）
const token0App = computed(() => {
  if (!sellToken.value) return defaultApp
  // 依赖applications数组长度使其响应式更新
  ams.Ams.applications()
  return ams.Ams.application(sellToken.value) || defaultApp
})

const token1App = computed(() => {
  if (!buyToken.value) return defaultApp
  // 依赖applications数组长度使其响应式更新
  ams.Ams.applications()
  return ams.Ams.application(buyToken.value) || defaultApp
})

const _latestPoints = computed(() => kline.Kline.latestPoints(selectedInterval.value, buyToken.value, sellToken.value).map((el) => {
  return {
    ...el,
    volume: el.base_volume,
    time: Math.floor(el.timestamp / 1000)
  }
}))

const klinePoints = ref([] as KLineData[])
const loading = ref(false)
const firstScreenReady = ref(false)
const backgroundHistoryQueued = ref(false)
const loadingDirection = ref(null as LoadDirection | null)
const pendingLoadDirections = ref([] as LoadDirection[])
const currentRequestId = ref(0)
const indicatorsReady = ref(false)
const startupBaselineRecorder = createStartupBaselineRecorder()
const startupInstrumentation = createStartupInstrumentation({
  emit: (event) => {
    startupBaselineRecorder.record(event)
    console.info('[PriceChartStartup]', JSON.stringify(event))
  }
})

const maxPointTimestamp = computed(() => klinePoints.value.length ? klinePoints.value.reduce((max, item) =>
  item.time > max.time ? item : max
).time * 1000 : (new Date()).getTime())
const minPointTimestamp = computed(() => klinePoints.value.length ? klinePoints.value.reduce((max, item) =>
  item.time < max.time ? item : max
).time * 1000 : poolCreatedAt.value)
const latestPoints = computed(() => _latestPoints.value.filter((el) => el.timestamp > maxPointTimestamp.value - 300000))
const backgroundHistoryStatus = computed(() => resolveBackgroundHistoryStatus({
  firstScreenReady: firstScreenReady.value,
  backgroundHistoryQueued: backgroundHistoryQueued.value,
  loadingDirection: loadingDirection.value,
  minPointTimestamp: minPointTimestamp.value,
  poolCreatedAt: poolCreatedAt.value
}))

watch(latestPoints, () => {
  if (!_latestPoints.value.length || !latestPoints.value.length) return

  latestPoints.value.forEach((point) => {
    if (point.timestamp < maxPointTimestamp.value) return

    const index = klinePoints.value.findIndex((el) => el.time === point.timestamp / 1000)
    if (index >= 0) klinePoints.value[index] = {
      ...point,
      time: Math.floor(point.timestamp / 1000)
    }
    else klinePoints.value.push({
      ...point,
      time: Math.floor(point.timestamp / 1000)
    })
  })
})

const getKline = (timestamp: number, reverse: boolean) => {
  if (!buyToken.value || !sellToken.value) return
  if (buyToken.value === sellToken.value) return

  const windowSize = getWindowSize(selectedInterval.value)
  const startAt = reverse ? (timestamp - windowSize) : timestamp + 1
  const endAt = reverse ? timestamp - 1 : (timestamp + windowSize)

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    startAt,
    endAt,
    interval: selectedInterval.value,
    reverse,
    requestId: currentRequestId.value,
  })
}

const fetchKlineRange = (startAt: number, endAt: number, reverse: boolean) => {
  if (!buyToken.value || !sellToken.value) return false
  if (buyToken.value === sellToken.value) return false

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    startAt,
    endAt,
    interval: selectedInterval.value,
    reverse,
    requestId: currentRequestId.value,
  })

  return true
}

const loadKline = (offset: number | undefined, limit: number | undefined, timestampBegin: number | undefined, timestampEnd: number | undefined, reverse: boolean) => {
  if (!buyToken.value || !sellToken.value) return false
  if (buyToken.value === sellToken.value) return false

  loading.value = true
  const loadRange = resolveLoadRange({
    timestampBegin,
    timestampEnd
  })
  const loadPayload: klineWorker.LoadPointsPayload = {
    token0: buyToken.value,
    token1: sellToken.value,
    offset: offset || 0,
    limit: limit || 100,
    interval: selectedInterval.value,
    reverse,
    requestId: currentRequestId.value,
  }

  if (loadRange.timestampBegin !== undefined) {
    loadPayload.timestampBegin = loadRange.timestampBegin
  }
  if (loadRange.timestampEnd !== undefined) {
    loadPayload.timestampEnd = loadRange.timestampEnd
  }

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_POINTS, loadPayload)

  return true
}

const getStoreKline = () => {
  if (buyToken.value && sellToken.value && buyToken.value !== sellToken.value && !loading.value) {
    console.log('[PriceChartView] getStoreKline called, interval:', selectedInterval.value)
    kline.Kline.subscribe(buyToken.value, sellToken.value, selectedInterval.value)
    currentRequestId.value += 1
    indicatorsReady.value = false
    startupInstrumentation.begin({
      requestId: currentRequestId.value,
      interval: selectedInterval.value,
      token0: buyToken.value,
      token1: sellToken.value
    })
    klinePoints.value = []
    firstScreenReady.value = false
    backgroundHistoryQueued.value = false
    pendingLoadDirections.value = []
    const startupPlan = resolveStartupRequestPlan({
      nowMs: Date.now(),
      interval: selectedInterval.value,
      poolCreatedAt: poolCreatedAt.value
    })

    loadKline(
      startupPlan.load.offset,
      startupPlan.load.limit,
      startupPlan.load.timestampBegin,
      startupPlan.load.timestampEnd,
      startupPlan.load.reverse
    )
    fetchKlineRange(
      startupPlan.fetchLatest.startAt,
      startupPlan.fetchLatest.endAt,
      startupPlan.fetchLatest.reverse
    )
  }
}

watch(buyToken, () => {
  // getStoreKline()
})

watch(sellToken, () => {
  // getStoreKline()
})

watch(selectedPool, (newPool, oldPool) => {
  if (loading.value) {
    loading.value = newPool?.poolApplication?.owner === oldPool?.poolApplication?.owner
  }
  if (!shouldRestartKlineOnSelectedPoolChange({
    previousPoolId: oldPool?.poolId,
    nextPoolId: newPool?.poolId,
  })) return

  getStoreKline()
})

watch(selectedInterval, () => {
  console.log('[PriceChartView] selectedInterval changed to:', selectedInterval.value)
  loading.value = false
  getStoreKline()
})

const updatePoints = (_points: kline.Point[], reason: Reason, reverse: boolean) => {
  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    originPoints: [...klinePoints.value].map((el) => {
      return {
        ...el,
        base_volume: el.volume,
        quote_volume: 'quote_volume' in el && typeof el.quote_volume === 'number' ? el.quote_volume : 0,
        timestamp: el.time * 1000
      } as kline.Point
    }),
    newPoints: _points,
    keepCount: -1, // -1 表示不限制，保留所有数据
    reverse,
    reason,
    requestId: currentRequestId.value,
  })
}

const onFetchedPoints = (payload: klineWorker.FetchedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, interval, reverse, requestId } = payload

  if (token0 !== buyToken.value || token1 !== sellToken.value) return
  if (requestId !== currentRequestId.value) return
  if (interval !== selectedInterval.value) return

  startupInstrumentation.markNetworkFetched({
    requestId,
    pointCount: _points.points.length
  })

  const windowSize = getWindowSize(selectedInterval.value)
  const startAt = reverse ? _points.start_at - windowSize : _points.end_at + 1
  const endAt = reverse ? _points.start_at - 1 : _points.end_at + windowSize

  const fetchSortDecision = resolveFetchSortDecision({
    reverse,
    startAt,
    endAt
  })

  updatePoints(_points.points, fetchSortDecision.reason, fetchSortDecision.reverse)
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, reverse, timestampBegin, timestampEnd, interval, requestId } = payload

  console.log('[PriceChartView] onLoadedPoints, interval:', interval, 'selectedInterval:', selectedInterval.value, 'points count:', _points.length)

  if (token0 !== buyToken.value || token1 !== sellToken.value) {
    loadKline(undefined, undefined, timestampBegin, timestampEnd, reverse)
    return
  }
  if (requestId !== currentRequestId.value) return

  // 检查 interval 是否匹配
  if (interval !== selectedInterval.value) {
    console.log('[PriceChartView] Interval mismatch, ignoring old data')
    return
  }

  startupInstrumentation.markCacheLoaded({
    requestId,
    pointCount: _points.length
  })

  const windowSize = getWindowSize(selectedInterval.value)
  const startAt = reverse ? (timestampBegin ?? minPointTimestamp.value) - windowSize : (timestampEnd ?? maxPointTimestamp.value) + 1
  const endAt = reverse ? (timestampBegin ?? minPointTimestamp.value) - 1 : (timestampEnd ?? maxPointTimestamp.value) + windowSize

  const reason = {
    reason: SortReason.LOAD,
    payload: {
      startAt,
      endAt
    }
  }

  updatePoints(_points, reason, reverse)
}

const onFetchSorted = (reverse: boolean, timestamp: number) => {
  getKline(timestamp, reverse)
}

const onLoadSorted = (reverse: boolean, timestamp: number) => {
  const windowSize = getWindowSize(selectedInterval.value)
  const timestampBegin = reverse ? (timestamp - windowSize) : timestamp + 1
  const timestampEnd = reverse ? timestamp - 1 : (timestamp + windowSize)

  loadKline(undefined, undefined, timestampBegin, timestampEnd, reverse)
}

const requestEdgeLoad = (direction: LoadDirection, timestamp: number) => {
  if (shouldDeferHistoryLoadUntilFirstPaint({
    direction,
    firstScreenReady: firstScreenReady.value
  })) {
    pendingLoadDirections.value = enqueueLoadDirection(pendingLoadDirections.value, direction)
    return
  }

  if (loading.value) {
    pendingLoadDirections.value = enqueueLoadDirection(pendingLoadDirections.value, direction)
    return
  }

  if (direction === 'new') {
    if (timestamp * 1000 < maxPointTimestamp.value) return
    loading.value = true
    loadingDirection.value = 'new'
    onLoadSorted(false, timestamp * 1000)
    return
  }

  if (timestamp * 1000 > minPointTimestamp.value) return
  loading.value = true
  loadingDirection.value = 'old'
  backgroundHistoryQueued.value = false
  onLoadSorted(true, timestamp * 1000)
}

const flushPendingLoad = () => {
  if (loading.value) return

  const { next, remaining } = dequeueLoadDirection(pendingLoadDirections.value)
  pendingLoadDirections.value = remaining

  if (!next) return

  const anchorTimestamp = next === 'new'
    ? Math.floor(maxPointTimestamp.value / 1000)
    : Math.floor(minPointTimestamp.value / 1000)

  requestEdgeLoad(next, anchorTimestamp)
}

const queueBackgroundHistoryBackfill = () => {
  if (!shouldScheduleBackgroundHistoryBackfill({
    firstScreenReady: firstScreenReady.value,
    backgroundHistoryQueued: backgroundHistoryQueued.value,
    minPointTimestamp: minPointTimestamp.value,
    poolCreatedAt: poolCreatedAt.value
  })) return

  backgroundHistoryQueued.value = true
  pendingLoadDirections.value = enqueueLoadDirection(pendingLoadDirections.value, 'old')
}

const finishLoading = (requestId: number) => {
  loading.value = false
  loadingDirection.value = null
  void nextTick(() => {
    if (!firstScreenReady.value) {
      firstScreenReady.value = true
      queueBackgroundHistoryBackfill()
    }
    startupInstrumentation.markFirstRender({
      requestId,
      pointCount: klinePoints.value.length
    })
    if (indicatorsReady.value) {
      startupInstrumentation.markIndicatorsReady({
        requestId,
        pointCount: klinePoints.value.length
      })
    }
    flushPendingLoad()
  })
}

const onIndicatorsReady = () => {
  indicatorsReady.value = true

  if (!firstScreenReady.value) return

  startupInstrumentation.markIndicatorsReady({
    requestId: currentRequestId.value,
    pointCount: klinePoints.value.length
  })
}

const onSortedPoints = (payload: klineWorker.SortedPointsPayload) => {
  const { points, token0, token1, reverse, reason, requestId } = payload
  const _reason = reason as Reason

  if (token0 !== buyToken.value || token1 !== sellToken.value) return
  if (requestId !== currentRequestId.value) return

  if (points.filter((el) => klinePoints.value.findIndex((_el) => _el.time * 1000 === el.timestamp) < 0).length === 0) {
    const timestamp = resolveNextFetchTimestamp({
      reverse,
      reason: _reason,
      minPointTimestamp: minPointTimestamp.value,
      maxPointTimestamp: maxPointTimestamp.value
    })
    if (timestamp < poolCreatedAt.value) return finishLoading(requestId)
    if (timestamp > new Date().getTime()) return finishLoading(requestId)
    return onFetchSorted(reverse, timestamp)
  }

  // 更新数据点
  klinePoints.value = points.map((el) => {
    return {
      ...el,
      volume: el.base_volume,
      time: Math.floor(el.timestamp / 1000)
    }
  })

  startupInstrumentation.markPointsMerged({
    requestId,
    pointCount: points.length,
    source: _reason.reason === SortReason.LOAD ? 'cache' : 'network'
  })

  // 内存管理：如果数据点过多，只保留最近的数据在内存中
  const maxMemoryPoints = getMaxPoints(selectedInterval.value)
  if (klinePoints.value.length > maxMemoryPoints * 1.5) {
    // 超过限制的 1.5 倍时，裁剪到限制数量
    console.log('[PriceChartView] Trimming memory, points:', klinePoints.value.length, 'max:', maxMemoryPoints)
    klinePoints.value = klinePoints.value.slice(-maxMemoryPoints)
  }

  finishLoading(requestId)
}

const onLoadNewData = (timestamp: number) => {
  requestEdgeLoad('new', timestamp)
}

const onLoadOldData = (timestamp: number) => {
  requestEdgeLoad('old', timestamp)
}

onBeforeMount(() => {
  loading.value = false
})

onMounted(() => {
  kline.Kline.initialize()
  installStartupBaselineDebug(startupBaselineRecorder, async () => {
    await dbKline.klinePoints.clear()
  })

  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)

  getStoreKline()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)
})

/*
const router = useRouter()

const onCreatePoolClick = () => {
  void router.push({
    path: '/create/pool',
    query: {
      token0: buyToken.value === constants.LINERA_NATIVE_ID ? sellToken.value : buyToken.value
    }
  })
}
*/

</script>

<style scoped lang="sass">
.kline
  border-top: 1px solid $grey-4
</style>
