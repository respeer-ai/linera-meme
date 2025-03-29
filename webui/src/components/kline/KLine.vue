<template>
  <div>
    <div class='token-pair-tip'>
      <SwapSelect />
    </div>
    <div id='chart' style="width:100%; height:600px"/>
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { init, dispose, Chart, Nullable, KLineData } from 'klinecharts'
import { kline, swap } from 'src/localstore'

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
  chart.value?.setPrecision({ price: 10 })
  chart.value?.applyNewData(points.value, true)
  getKline()
})

onBeforeUnmount(() => {
  dispose('chart')
})

</script>

<style scoped lang="sass">
*
  margin: 0
  padding: 0

#chart-container
  position: relative
  height: 50vh
  min-height: 700px
  display: block
  overflow: auto

.token-pair-tip
  width: 63%
  display: inline-block
  vertical-align: middle

.token-pair-tip img
  width: 1.5rem
  border: 2px solid #dadada
  border-radius: 0.7rem
  display: inline-block
  vertical-align: middle

.token-pair-tip div
  margin-left: 5px
  font-size: 0.9rem
  font-weight: bold
  color: #555
  display: inline-block
  vertical-align: middle

.radio-buttons-tip
  width: 37%
  display: inline-block
  vertical-align: middle
  text-align: right

.radio-buttons
  display: inline-block
  padding: 2px
  background-color: #dadada
  border-radius: 5px

.radio-buttons:hover *
  cursor: pointer

.radio-button
  display: inline-block

.radio-input
  display: none

.radio-lable
  width: 2rem
  margin: 1px
  font-size: 0.8rem
  border-radius: 3px
  background-color: #e5e5e5
  text-align: center
  display: inline-block
  color: gray

.radio-input:checked+label
  display: inline-block
  color: black
  background-color: #eee
  font-weight: bold
</style>
