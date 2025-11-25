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
import { init, dispose, Chart, Nullable, KLineData, Options, LoadDataParams, LoadDataType } from 'klinecharts'
import { kline, swap } from 'src/localstore'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'
import { klineWorker } from 'src/worker'
import { uid } from 'quasar'

import SwapSelect from './SwapSelect.vue'
import { _Indicator } from './Indicator'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000 || 0))

type CallbackFunc = (dataList: KLineData[], more?: boolean) => void
const callbacks = ref(new Map<string, CallbackFunc>())

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

const getKline = (startAt: number, reverse: boolean) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  startAt = reverse ? startAt - 1 * 3600 : startAt
  const endAt = reverse ? startAt : startAt + 1 * 3600

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.FETCH_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE
  })
}

const loadKline = (offset: number, limit: number, reverse: boolean, callbackId?: string) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  klineWorker.KlineWorker.send(klineWorker.KlineEventType.LOAD_POINTS, {
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    offset,
    limit,
    interval: kline.Interval.ONE_MINUTE,
    reverse,
    priv: callbackId ? {
      callbackId
    } : {}
  })
}

const getStoreKline = () => {
  if (selectedToken0.value && selectedToken1.value && selectedToken0.value !== selectedToken1.value) {
    chart.value?.clearData()
    loadKline(0, 100, true)
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

type CallPriv = {
    callbackId?: string
  }

type ReasonPayload = {
  endAt: number,
  priv: CallPriv
} | {
  offset: number,
  limit: number,
  priv: CallPriv
}

interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

const LoadRemote = ref(false)

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
  const { token0, token1, priv } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  updatePoints(_points.points, {
    reason: SortReason.FETCH,
    payload: {
      endAt: _points.end_at,
      priv: priv as CallPriv
    }
  })
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points
  const { token0, token1, priv } = payload

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  let fetchStartAt = Math.floor(Math.max(latestTimestamp.value / 1000, poolCreatedAt.value / 1000 || 0))
  fetchStartAt = Math.floor(fetchStartAt / 60) * 60

  LoadRemote.value = _points.length === 0

  const reason = {
    reason: _points.length ? SortReason.LOAD : SortReason.FETCH,
    payload: _points.length ? {
      offset: payload.offset + payload.limit,
      limit: payload.limit,
      priv: priv as CallPriv
    } : {
      endAt: fetchStartAt,
      priv: priv as CallPriv
    }
  }

  updatePoints(_points, reason)
}

const onFetchSorted = (payload: ReasonPayload, reverse: boolean) => {
  const { endAt } = payload as { endAt: number }

  if (endAt > Math.floor(Date.now() / 1000)) {
    applied.value = true
    return
  }

  setTimeout(() => {
    getKline(endAt, reverse)
  }, 100)
}

const onLoadSorted = (payload: ReasonPayload, reverse: boolean) => {
  const { offset, limit, priv } = payload as { offset: number, limit: number, priv: CallPriv }

  loadKline(offset, limit, reverse, priv.callbackId)
}

const LoadReason = ref(undefined as unknown as ReasonPayload)

const onSortedPoints = (payload: klineWorker.SortedPointsPayload) => {
  const { points, reason, token0, token1 } = payload
  const _reason = reason as Reason

  if (token0 !== selectedToken0.value || token1 !== selectedToken1.value) return

  LoadReason.value = _reason.payload

  if (_reason.payload.priv?.callbackId) {
    const _callback = callbacks.value.get(_reason.payload.priv?.callbackId)
    if (_callback) {
      const dataList = chart.value?.getDataList() || []
      const _points = points.filter((el) => dataList.findIndex((_el) => _el.timestamp === el.timestamp) < 0)
      _callback(_points as KLineData[], _points.length > 0)
      callbacks.value.delete(_reason.payload.priv?.callbackId)
    }
  } else {
    chart.value?.applyNewData(points as KLineData[])
  }
  latestTimestamp.value = points[points.length - 1]?.timestamp || latestTimestamp.value
}

const loadMore = (params: LoadDataParams) => {
  const callbackId = uid()
  callbacks.value.set(callbackId, params.callback)
  LoadReason.value.priv = { callbackId }

  if (LoadRemote.value) {
    onFetchSorted(LoadReason.value, params.type === LoadDataType.Backward)
  } else {
    onLoadSorted(LoadReason.value, params.type === LoadDataType.Backward)
  }
}

onMounted(() => {
  chart.value = init('chart', {
    layout: [
      {
        type: 'candle',
        content: [
          _Indicator.movingAverage,
          _Indicator.exponentialMovingAverage
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

  chart.value?.setPriceVolumePrecision(10, 6)
  chart.value?.setLoadDataCallback(loadMore)

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
