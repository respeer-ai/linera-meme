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

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)

const points = computed(() => _kline._points(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[])
const lastTimestamp = computed(() => points.value[points.value.length - 1]?.timestamp || 0)

const chart = ref<Nullable<Chart>>()
const applied = ref(false)

watch(lastTimestamp, () => {
  if (!applied.value) return
  chart.value?.applyNewData(points.value)
})

const getKline = (startAt: number) => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  const endAt = startAt + 3 * 3600

  _kline.getKline({
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt,
    endAt,
    interval: kline.Interval.ONE_MINUTE
  }, (error: boolean) => {
    if (error) return
    chart.value?.applyNewData(points.value, true)
    if (endAt > Math.floor(Date.now() / 1000)) {
      applied.value = true
      return
    }
    setTimeout(() => {
      getKline(endAt)
    }, 100)
  })
}

const getPoolKline = () => {
  if (selectedPool.value?.createdAt) {
    getKline(Math.floor(selectedPool.value?.createdAt / 1000000))
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
  chart.value?.applyNewData(points.value)
  getPoolKline()
})

onBeforeUnmount(() => {
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
