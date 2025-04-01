<template>
  <div>
    <div class='row'>
      <div :style='{marginLeft: "4px"}'>
        <SwapSelect />
      </div>
      <q-space />
      <q-btn
        flat label='Create pool' class='text-blue-8' rounded :style='{margin: "4px 0"}'
        @click='onCreatePoolClick'
      />
    </div>
    <q-separator />
    <div id='chart' style='width:100%; height:600px' />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { init, dispose, Chart, Nullable, KLineData } from 'klinecharts'
import { kline, swap } from 'src/localstore'
import { useRouter } from 'vue-router'
import { constants } from 'src/constant'

import SwapSelect from './SwapSelect.vue'

const _kline = kline.useKlineStore()
const _swap = swap.useSwapStore()

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)

const points = computed(() => _kline._points(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[])
const latestPoints = computed(() => _kline._latestPoints(kline.Interval.ONE_MINUTE, selectedToken0.value, selectedToken1.value) as KLineData[])

const chart = ref<Nullable<Chart>>()

watch(latestPoints, () => {
  latestPoints.value.forEach((point) => {
    chart.value?.updateData(point)
  })
})

const getKline = () => {
  if (!selectedToken0.value || !selectedToken1.value) return
  if (selectedToken0.value === selectedToken1.value) return

  _kline.getKline({
    token0: selectedToken0.value,
    token1: selectedToken1.value,
    startAt: Math.floor(Date.now() / 1000 - 24 * 3600 * 90),
    endAt: Math.floor(Date.now() / 1000),
    interval: kline.Interval.ONE_MINUTE
  }, (error: boolean) => {
    if (error) return
    chart.value?.applyNewData(points.value, true)
  })
}

watch(selectedToken0, () => {
  getKline()
})

watch(selectedToken1, () => {
  getKline()
})

onMounted(() => {
  chart.value = init('chart')
  chart.value?.setPrecision({ price: 8 })
  chart.value?.applyNewData(points.value, true)
  getKline()
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
#chart-container
  position: relative
  height: 50vh
  min-height: 700px
  display: block
  overflow: auto
  background: red
</style>
