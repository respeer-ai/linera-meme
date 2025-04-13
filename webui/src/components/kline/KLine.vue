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

import SwapSelect from './SwapSelect.vue'
import { klineWorker } from 'src/worker'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolCreatedAt = computed(() => Math.floor(selectedPool.value?.createdAt / 1000000 || 0))

const latestTimestamp = ref(poolCreatedAt.value)
const latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value).filter((el) => el.timestamp > latestTimestamp.value) as KLineData[])

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
    latestTimestamp.value = _kline.latestTimestamp(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) || poolCreatedAt.value
    latestTimestamp.value = Math.max(latestTimestamp.value, Math.floor(Date.now() / 1000 - 1 * 3600))
    getKline(latestTimestamp.value)
  }
}

watch(selectedToken0, () => {
  getPoolKline()
})

watch(selectedToken1, () => {
  getPoolKline()
})

watch(selectedPool, () => {
  getPoolKline()
})

const onPoints = (payload: klineWorker.FetchedPointsPayload) => {
  const r = new Map<string, kline.Points[]>()
  r.set(payload.interval, [payload])
  _kline.onKline(r)

  const points = _kline._points(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[]
  chart.value?.applyNewData(points)
  latestTimestamp.value = _kline.latestTimestamp(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) || latestTimestamp.value

  if (payload.end_at > Math.floor(Date.now() / 1000)) {
    applied.value = true
    return
  }

  setTimeout(() => {
    getKline(payload.end_at)
  }, 100)
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

  const points = _kline._points(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[]
  chart.value?.applyNewData(points)

  klineWorker.KlineWorker.on(klineWorker.KlineEventType.FETCHED_POINTS, onPoints as klineWorker.ListenerFunc)

  getPoolKline()
})

onBeforeUnmount(() => {
  klineWorker.KlineWorker.off(klineWorker.KlineEventType.FETCHED_POINTS, onPoints as klineWorker.ListenerFunc)
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
