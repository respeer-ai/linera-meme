<template>
  <div>
    <div class='row kline'>
      <div :style='{marginLeft: "4px"}'>
        <SwapSelect />
      </div>
      <q-space />
      <q-btn
        flat
        label='Create pool'
        class='text-blue-8'
        rounded
        :style='{margin: "4px 0"}'
        @click='onCreatePoolClick'
      />
    </div>
    <q-separator />
    <div id='chart' style='width:100%; height:600px' />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { init, dispose, Chart, Nullable, KLineData, Options } from 'klinecharts'
import { kline, swap } from 'src/localstore'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'
import { klineWorker } from 'src/worker'

import SwapSelect from './SwapSelect.vue'
import { _Indicator } from './Indicator'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000 || 0))

const latestTimestamp = ref(poolCreatedAt.value)
const _latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[])
const latestPoints = computed(() => _latestPoints.value.filter((el) => el.timestamp > latestTimestamp.value - 300000))

const chart = ref<Nullable<Chart>>()
const applied = ref(false)

watch(latestPoints, () => {
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
})

const getKline = (startAt: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const endAt = startAt + 1 * 3600

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE
  })
}

const loadKline = (offset: number, limit: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    offset,
    limit,
    interval: kline.Interval.ONE_MINUTE
  })
}

const getStoreKline = () => {
  if (selectedToken0.value && selectedToken1.value && selectedToken0.value !== selectedToken1.value) {
    chart.value?.clearData()
    loadKline(0, 100)
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

type ReasonPayload = { endAt: number } | { offset: number, limit: number }

interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

const updatePoints = (_points: kline.Point[], reason: Reason) => {
  klineWorker.KlineWorker.send(klineWorker.KlineEventType.SORT_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    originPoints: [...(chart.value?.getDataList() || [])].map((el) => {
      return { ...el } as kline.Point
    }),
    newPoints: _points,
    keepCount: MAX_POINTS,
    reverse: false,
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
      endAt: _points.end_at
    }
  })
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1 } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  let fetchStartAt = Math.floor(Math.max(latestTimestamp.value / 1000, poolCreatedAt.value / 1000 || 0))
  fetchStartAt = Math.floor(fetchStartAt / 60) * 60

  const reason = {
    reason: _points.length ? SortReason.LOAD : SortReason.FETCH,
    payload: _points.length ? {
      offset: payload.offset + payload.limit,
      limit: payload.limit
    } : {
      endAt: fetchStartAt
    }
  }

  updatePoints(_points, reason)
}

const onFetchSorted = (payload: ReasonPayload) => {
  const { endAt } = payload as { endAt: number }

  if (endAt > Math.floor(Date.now() / 1000)) {
    applied.value = true
    return
  }

  setTimeout(() => {
    getKline(endAt)
  }, 100)
}

const onLoadSorted = (payload: ReasonPayload) => {
  const { offset, limit } = payload as { offset: number, limit: number }

  loadKline(offset, limit)
}

const onSortedPoints = (payload: klineWorker.SortedPointsPayload) => {
  const { points, reason, token0, token1 } = payload
  const _reason = reason as Reason

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  chart.value?.applyNewData(points as KLineData[])
  latestTimestamp.value = points[points.length - 1]?.timestamp || latestTimestamp.value

  switch (_reason.reason) {
    case SortReason.FETCH:
      return onFetchSorted(_reason.payload)
    case SortReason.LOAD:
      return onLoadSorted(_reason.payload)
  }
}

onMounted(() => {
  chart.value = init('chart', {
    layout: [
      {
        type: 'candle',
        content: [
          _Indicator.movingAverage,
          _Indicator.exponentialMovingAverate
        ],
        options: { order: Number.MIN_SAFE_INTEGER }
      },
      {
        type: 'indicator',
        content: [
          _Indicator.volume
        ],
        options: { order: 10 }
      },
      { type: 'xAxis', options: { order: 9 } }
    ]
  } as unknown as Options)

  chart.value?.setPrecision({ price: 10, volume: 4 })

  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)

  getStoreKline()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.SORTED_POINTS, onSortedPoints as klineWorker.ListenerFunc)
  dispose('chart')
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
