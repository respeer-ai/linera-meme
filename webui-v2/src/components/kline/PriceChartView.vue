<template>
  <div :style='{ height: height }'>
    <chart-view
      style='width:100%;'
      :data='klinePoints'
      @load-new-data='onLoadNewData'
      @load-old-data='onLoadOldData'
      :height='height'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch, onBeforeMount, toRef } from 'vue'
import { kline, swap } from 'src/stores/export'
// import { useRouter } from 'vue-router'
import { klineWorker } from 'src/worker'
import { KLineData } from './chart/KlineData'

import ChartView from './chart/ChartView.vue'

const props = defineProps({
  height: { type: String, default: '550px' }
})
const height = toRef(props, 'height')

const buyToken = computed(() => swap.Swap.buyToken())
const sellToken = computed(() => swap.Swap.sellToken())
const selectedPool = computed(() => swap.Swap.selectedPool())
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000) || 0)

const _latestPoints = computed(() => kline.Kline.latestPoints(kline.Interval.ONE_MINUTE, buyToken.value, sellToken.value).map((el) => {
  return {
    ...el,
    time: Math.floor(el.timestamp / 1000)
  }
}))

const klinePoints = ref([] as KLineData[])
const loading = ref(false)

const maxPointTimestamp = computed(() => klinePoints.value.length ? klinePoints.value.reduce((max, item) =>
  item.time > max.time ? item : max
).time * 1000 : (new Date()).getTime())
const minPointTimestamp = computed(() => klinePoints.value.length ? klinePoints.value.reduce((max, item) =>
  item.time < max.time ? item : max
).time * 1000 : poolCreatedAt.value)
const latestPoints = computed(() => _latestPoints.value.filter((el) => el.timestamp > maxPointTimestamp.value - 300000))

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

  const startAt = reverse ? (timestamp - 1 * 3600 * 1000) : timestamp + 1
  const endAt = reverse ? timestamp - 1 : (timestamp + 1 * 3600 * 1000)

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE,
    reverse
  })
}

const loadKline = (offset: number | undefined, limit: number | undefined, timestampBegin: number | undefined, timestampEnd: number | undefined, reverse: boolean) => {
  if (!buyToken.value || !sellToken.value) return false
  if (buyToken.value === sellToken.value) return false

  loading.value = true

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    offset: offset || 0,
    limit: limit || 100,
    interval: kline.Interval.ONE_MINUTE,
    reverse,
    timestampBegin: timestampBegin || 0,
    timestampEnd: timestampEnd || 0
  })

  return true
}

const getStoreKline = () => {
  if (buyToken.value && sellToken.value && buyToken.value !== sellToken.value && !loading.value) {
    klinePoints.value = []

    loadKline(0, 100, undefined, undefined, true)
  }
}

watch(buyToken, () => {
  // getStoreKline()
})

watch(sellToken, () => {
  // getStoreKline()
})

watch(selectedPool, () => {
  loading.value = false
  getStoreKline()
})

const MAX_POINTS = 1800

enum SortReason {
  FETCH = 'Fetch',
  LOAD = 'Load'
}

type ReasonPayload = {
  startAt: number,
  endAt: number,
}

interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

const updatePoints = (_points: kline.Point[], reason: Reason, reverse: boolean) => {
  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_POINTS, {
    token0: buyToken.value,
    token1: sellToken.value,
    originPoints: [...klinePoints.value].map((el) => {
      return {
        ...el,
        timestamp: el.time * 1000
      } as kline.Point
    }),
    newPoints: _points,
    keepCount: MAX_POINTS,
    reverse,
    reason
  })
}

const onFetchedPoints = (payload: klineWorker.FetchedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, reverse } = payload

  if (token0 !== buyToken.value || token1 !== sellToken.value) return

  const startAt = reverse ? _points.start_at - 1 * 3600 * 1000 : _points.end_at + 1
  const endAt = reverse ? _points.start_at - 1 : _points.end_at + 1 * 3600 * 1000

  updatePoints(_points.points, {
    reason: SortReason.FETCH,
    payload: {
      startAt,
      endAt
    }
  }, true)
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, reverse, timestampBegin, timestampEnd } = payload

  if (token0 !== buyToken.value || token1 !== sellToken.value) {
    loadKline(undefined, undefined, timestampBegin, timestampEnd, reverse)
    return
  }

  const startAt = reverse ? (timestampBegin ?? minPointTimestamp.value) - 1 * 3600 * 1000 : (timestampEnd ?? maxPointTimestamp.value) + 1
  const endAt = reverse ? (timestampBegin ?? minPointTimestamp.value) - 1 : (timestampEnd ?? maxPointTimestamp.value) + 1 * 3600 * 1000

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
  const timestampBegin = reverse ? (timestamp - 1 * 3600 * 1000) : timestamp + 1
  const timestampEnd = reverse ? timestamp - 1 : (timestamp + 1 * 3600 * 1000)

  loadKline(undefined, undefined, timestampBegin, timestampEnd, reverse)
}

const onSortedPoints = (payload: klineWorker.SortedPointsPayload) => {
  const { points, token0, token1, reverse, reason } = payload
  const _reason = reason as Reason

  if (token0 !== buyToken.value || token1 !== sellToken.value) return

  if (points.filter((el) => klinePoints.value.findIndex((_el) => _el.time * 1000 === el.timestamp) < 0).length === 0) {
    let timestamp = reverse ? maxPointTimestamp.value : minPointTimestamp.value
    if (_reason.reason === SortReason.FETCH) {
      timestamp = reverse ? _reason.payload.startAt : _reason.payload.endAt
    }
    if (timestamp < poolCreatedAt.value) return
    if (timestamp > new Date().getTime()) return
    return onFetchSorted(reverse, timestamp)
  }

  klinePoints.value = points.map((el) => {
    return {
      ...el,
      time: Math.floor(el.timestamp / 1000)
    }
  })

  loading.value = false
}

const onLoadNewData = (timestamp: number) => {
  if (loading.value) return
  loading.value = true
  if (timestamp * 1000 < maxPointTimestamp.value) return
  onLoadSorted(false, timestamp * 1000)
}

const onLoadOldData = (timestamp: number) => {
  if (loading.value) return
  loading.value = true
  if (timestamp * 1000 > minPointTimestamp.value) return
  onLoadSorted(true, timestamp * 1000)
}

onBeforeMount(() => {
  loading.value = false
})

onMounted(() => {
  kline.Kline.initialize()

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
