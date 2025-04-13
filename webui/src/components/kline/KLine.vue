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

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000000 || 0))

const latestTimestamp = ref(poolCreatedAt.value)
const latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value).filter((el) => el.timestamp > latestTimestamp.value) as KLineData[])
const points = ref([] as KLineData[])

const chart = ref<Nullable<Chart>>()
const applied = ref(false)

watch(latestPoints, () => {
  if (!applied.value) return
  latestPoints.value.forEach((point) => {
    chart.value?.updateData(point)
    latestTimestamp.value = point.timestamp
  })
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

const getPoolKline = () => {
  if (selectedPool.value?.createdAt) {
    latestTimestamp.value = Math.max(poolCreatedAt.value, Math.floor(Date.now() / 1000 - 1 * 3600))
    getKline(latestTimestamp.value)
  }
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

const MAX_POINTS = 300

const updatePoints = (_points: KLineData[]) => {
  // TODO: load according to window
  _points.forEach((point) => {
    const index = points.value.findIndex((el) => el.timestamp === point.timestamp)
    index >= 0 ? (points.value[index] = point) : points.value.push(point)
  })
  points.value.sort((p1, p2) => p1.timestamp - p2.timestamp)

  points.value = points.value.slice(Math.max(points.value.length - MAX_POINTS, 0))
}

const onFetchedPoints = (payload: klineWorker.FetchedPointsPayload) => {
  const _points = payload.points as KLineData[]

  updatePoints(_points)

  chart.value?.applyNewData(points.value)
  latestTimestamp.value = _points[_points.length - 1]?.timestamp || latestTimestamp.value

  if (payload.end_at > Math.floor(Date.now() / 1000)) {
    applied.value = true
    return
  }

  setTimeout(() => {
    getKline(payload.end_at)
  }, 100)
}

const onLoadedPoints = (payload: klineWorker.LoadedPointsPayload) => {
  const _points = payload.points as KLineData[]

  updatePoints(_points)

  chart.value?.applyNewData(points.value)
  latestTimestamp.value = _points[_points.length - 1]?.timestamp || latestTimestamp.value

  if (_points.length) loadKline(payload.offset + payload.limit, payload.limit)
  else getPoolKline()
}

onMounted(() => {
  chart.value = init('chart', {
    layout: [
      {
        type: 'candle',
        content: ['MA', { name: 'EMA', calcParams: [5, 10, 30, 60] }],
        options: { order: Number.MIN_SAFE_INTEGER }
      },
      { type: 'indicator', content: ['VOL'], options: { order: 10 } },
      { type: 'xAxis', options: { order: 9 } }
    ]
  } as unknown as Options)
  chart.value?.setPrecision({ price: 10, volume: 4 })

  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.on(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)

  getStoreKline()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_POINTS, onFetchedPoints as klineWorker.ListenerFunc)
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.LOADED_POINTS, onLoadedPoints as klineWorker.ListenerFunc)
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
