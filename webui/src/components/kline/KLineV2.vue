<template>
  <div>
    <div class='row kline'>
      <div :style='{marginLeft: "4px"}'>
        <SwapSelect />
      </div>
      <q-space />
      <q-btn
        dense
        flat
        label='Create pool'
        class='text-blue-8'
        rounded
        :style='{margin: "0 0"}'
        @click='onCreatePoolClick'
      />
    </div>
    <q-separator />
    <Chart
      style='width:100%'
      :data='klinePoints'
      @load-new-data='onLoadNewData'
      @load-old-data='onLoadOldData'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { kline, swap } from 'src/localstore'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'
import { klineWorker } from 'src/worker'
import { dbBridge } from 'src/bridge'
import { KLineData } from './chart/KlineData'

import SwapSelect from './SwapSelect.vue'
import { _Indicator } from './Indicator'
import Chart from './chart/Chart.vue'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000 || 0))

const latestTimestamp = ref(poolCreatedAt.value)
const _latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value).map((el) => {
  return {
    ...el,
    time: Math.floor(el.timestamp / 1000)
  }
}))
const latestPoints = computed(() => _latestPoints.value.filter((el) => el.timestamp > latestTimestamp.value - 300000))

const applied = ref(false)
const klinePoints = ref([] as KLineData[])

const maxPointTimestamp = computed(() => klinePoints.value.reduce((max, item) =>
  item.time > max.time ? item : max
).time)
const minPointTimestamp = computed(() => klinePoints.value.reduce((max, item) =>
  item.time < max.time ? item : max
).time)

watch(latestPoints, () => {
  /*
  if (!applied.value || !_latestPoints.value.length) return

  const dataList = chart.value?.getDataList()
  if (!dataList?.length) {
    chart.value?.applyNewData(_latestPoints.value)
    latestTimestamp.value = _latestPoints.value[_latestPoints.value.length - 1]?.timestamp
    return
  }

  if (!latestPoints.value.length) return
  const maxTimestamp = dataList[dataList.length - 1].timestamp

  if (maxTimestamp < latestPoints.value[0].timestamp) {
    latestPoints.value.forEach((point) => {
      chart.value?.updateData(point)
    })
    latestTimestamp.value = latestPoints.value[latestPoints.value.length - 1].timestamp
    return
  }

  const length = dataList.length
  let startIndex = dataList.length - 1

  for (let i = startIndex; i >= 0; i--) {
    if (dataList[i].timestamp === latestPoints.value[0].timestamp) {
      startIndex = i
      break
    }
  }
  for (let i = startIndex, j = 0; j < latestPoints.value.length - 1; i++, j++) {
    if (i < length) dataList[i] = latestPoints.value[j]
    else dataList.push(latestPoints.value[j])
  }
  chart.value?.updateData(latestPoints.value[latestPoints.value.length - 1])
  latestTimestamp.value = latestPoints.value[latestPoints.value.length - 1].timestamp
  */
})

const getKline = (timestamp: number, reverse: boolean) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const startAt = reverse ? (timestamp - 1 * 3600 * 1000) : timestamp + 1
  const endAt = reverse ? timestamp - 1 : (timestamp + 1 * 3600 * 1000)

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE
  })
}

const loadKline = (offset: number | undefined, limit: number | undefined, timestampBegin: number | undefined, timestampEnd: number | undefined, reverse: boolean) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    offset,
    limit,
    interval: kline.Interval.ONE_MINUTE,
    reverse,
    timestampBegin,
    timestampEnd
  })
}

const getStoreKline = async () => {
  if (selectedToken0.value && selectedToken1.value && selectedToken0.value !== selectedToken1.value) {
    klinePoints.value = []

    loadKline(0, 100, undefined, undefined, true)
  }
}

watch(selectedToken0, async () => {
  await getStoreKline()
})

watch(selectedToken1, () => {
  getStoreKline()
})

watch(selectedPool, () => {
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
    token0: selectedToken0.value,
    token1: selectedToken1.value,
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
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  updatePoints(_points.points, {
    reason: SortReason.FETCH,
    payload: {
      startAt: _points.end_at,
      endAt: _points.end_at + 1 * 3600
    }
  // TODO: reverse
  }, true)
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, reverse, timestampBegin, timestampEnd } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  const _latestTimestamp = Math.max(latestTimestamp.value, poolCreatedAt.value || 0)

  const startAt = reverse ? (timestampBegin ?? _latestTimestamp) - 1 * 3600 * 1000 : (timestampEnd ?? _latestTimestamp) + 1
  const endAt = reverse ? (timestampBegin ?? _latestTimestamp) - 1 : (timestampEnd ?? _latestTimestamp) + 1 * 3600 * 1000

  const reason = {
    reason: _points.length ? SortReason.LOAD : SortReason.FETCH,
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
  const { points, token0, token1, reverse } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  if (points.filter((el) => klinePoints.value.findIndex((_el) => _el.time * 1000 !== el.timestamp)).length === 0) {
    const timestamp = reverse ? maxPointTimestamp.value * 1000 : minPointTimestamp.value * 1000
    return onFetchSorted(reverse, timestamp)
  }

  klinePoints.value = points.map((el) => {
    return {
      ...el,
      time: Math.floor(el.timestamp / 1000)
    }
  })
}

const onLoadNewData = (timestamp: number) => {
  if (timestamp < maxPointTimestamp.value) return
  onLoadSorted(false, timestamp * 1000)
}

const onLoadOldData = (timestamp: number) => {
  if (timestamp > minPointTimestamp.value) return
  onLoadSorted(true, timestamp * 1000)
}

onMounted(async () => {
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)

  await getStoreKline()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)
})

const router = useRouter()

const onCreatePoolClick = () => {
  void router.push({
    path: '/create/pool',
    query: {
      token0: selectedToken0.value === constants.LINERA_NATIVE_ID ? selectedToken1.value : selectedToken0.value
    }
  })
}

</script>

<style scoped lang="sass">
.kline
  border-top: 1px solid $grey-4
</style>
