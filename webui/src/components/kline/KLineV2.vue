<template>
  <div style='height: 550px'>
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
        :style='{margin: "4px 0"}'
        @click='onCreatePoolClick'
      />
    </div>
    <q-separator />
    <Chart
      style='width:100%; height: 550px;'
      :data='klinePoints'
      @load-new-data='onLoadNewData'
      @load-old-data='onLoadOldData'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch, onBeforeMount } from 'vue'
import { kline, swap } from 'src/localstore'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'
import { klineWorker } from 'src/worker'
import { KLineData } from './chart/KlineData'

import SwapSelect from './SwapSelect.vue'
import Chart from './chart/Chart.vue'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000) || 0)

const _latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value).map((el) => {
  return {
    ...el,
    time: Math.floor(el.timestamp / 1000)
  }
}))

const klinePoints = ref([] as KLineData[])
const loadingNew = ref(false)
const loadingOld = ref(false)

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
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const startAt = reverse ? (timestamp - 1 * 3600 * 1000) : timestamp + 1
  const endAt = reverse ? timestamp - 1 : (timestamp + 1 * 3600 * 1000)

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE,
    reverse
  })
}

const loadKline = (offset: number | undefined, limit: number | undefined, timestampBegin: number | undefined, timestampEnd: number | undefined, reverse: boolean) => {
  if (!selectedToken0.value || !selectedToken1.value) return false
  if (selectedToken0.value === selectedToken1.value) return false

  reverse ? loadingOld.value = true : loadingNew.value = true

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

  return true
}

const getStoreKline = () => {
  if (selectedToken0.value && selectedToken1.value && selectedToken0.value !== selectedToken1.value && !loadingOld.value) {
    klinePoints.value = []

    loadKline(0, 100, undefined, undefined, true)
  }
}

watch(selectedToken0, () => {
  getStoreKline()
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
  const { token0, token1, reverse } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  const startAt = reverse ? _points.start_at - 1 * 3600 * 1000 : _points.end_at + 1
  const endAt = reverse ? _points.start_at - 1 : _points.end_at + 1 * 3600 * 1000

  updatePoints(_points.points, {
    reason: SortReason.FETCH,
    payload: {
      startAt,
      endAt
    }
  }, reverse)
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, reverse, timestampBegin, timestampEnd } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) {
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

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  if (points.filter((el) => klinePoints.value.findIndex((_el) => _el.time * 1000 === el.timestamp) < 0).length === 0) {
    let timestamp = reverse ? minPointTimestamp.value : maxPointTimestamp.value
    if (_reason.reason === SortReason.FETCH) {
      timestamp = reverse ? _reason.payload.startAt : _reason.payload.endAt
    }
    if (timestamp < poolCreatedAt.value) {
      reverse ? loadingOld.value = false : loadingNew.value = false
      return
    }
    if (timestamp > new Date().getTime()) {
      reverse ? loadingOld.value = false : loadingNew.value = false
      return
    }
    return onFetchSorted(reverse, timestamp)
  }

  klinePoints.value = points.map((el) => {
    return {
      ...el,
      time: Math.floor(el.timestamp / 1000)
    }
  })

  reverse ? loadingOld.value = false : loadingNew.value = false
}

const onLoadNewData = (timestamp: number) => {
  if (loadingNew.value) return
  if (timestamp * 1000 < maxPointTimestamp.value) return
  loadingNew.value = true
  onLoadSorted(false, timestamp * 1000)
}

const onLoadOldData = (timestamp: number) => {
  if (loadingOld.value) return
  if (timestamp * 1000 > minPointTimestamp.value) return
  loadingOld.value = true
  onLoadSorted(true, timestamp * 1000)
}

onBeforeMount(() => {
  loadingOld.value = false
  loadingNew.value = false
})

onMounted(() => {
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
