<template>
  <div>
    <div style='padding: 5px;width: 100%;'>
      <div class='token-pair-tip'>
        <SwapSelect />
      </div>
      <div class='radio-buttons-tip'>
        <div class='radio-buttons'>
          <div class='radio-button' v-for='(val,idx) in [] as Array<KPoint>' :key='idx' :value='val.KPointType'>
            <input
              class='radio-input'
              type='radio'
              :id='val.KPointType'
              :value='val.KPointType'
              v-model='selectedKPType'
              :checked='idx==0'
            >
            <label class='radio-lable' :for='val.KPointType'>{{ val.ShortName }}</label>
          </div>
        </div>
      </div>
    </div>
    <div id='chart-container' />
  </div>
</template>

<script setup lang='ts'>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { initEchart, setStartAndEnd } from './KLineOption'
import * as echarts from 'echarts/core'

import SwapSelect from './SwapSelect.vue'

const selectedKPType = ref('')

let myChart: echarts.ECharts

interface KPoint {
  KPointType: string
  ShortName: string
}

interface eventParams {
  type: string
  start?: number
  end?: number
  batch?: {
    start: number
    end: number
  }[]
}

onMounted(() => {
  myChart = initEchart('chart-container')
  myChart.on('datazoom', (params) => {
    const _params = params as eventParams
    const start: number | undefined = _params.start || _params.batch?.[0].start
    const end: number | undefined = _params.end || _params.batch?.[0].end
    if (start === undefined || start < 1) {
      setStartAndEnd(myChart, 1, end || 0)
    }
  })
})

onBeforeUnmount(() => {
  myChart.dispose()
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
