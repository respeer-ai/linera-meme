<template>
  <q-btn-dropdown
    :label='currentLabel'
    :icon='currentIcon'
    unelevated
    dense
    no-caps
    color='dark-secondary'
    text-color='neutral'
    dropdown-icon='expand_more'
    class='radius-8'
    style='min-width: 120px;'
  >
    <q-list dense class='bg-dark-secondary text-neutral'>
      <q-item
        v-for='type in chartTypes'
        :key='type.value'
        clickable
        v-close-popup
        @click='model = type.value'
        :active='model === type.value'
        active-class='bg-primary text-white'
      >
        <q-item-section avatar>
          <q-icon :name='type.icon' size='20px' />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ type.label }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { ChartType } from './ChartType'

const chartTypes = [
  { value: ChartType.CANDLESTICK, label: '蜡烛图', icon: 'candlestick_chart' },
  { value: ChartType.LINE, label: '折线图', icon: 'show_chart' },
  { value: ChartType.AREA, label: '面积图', icon: 'area_chart' }
]

const model = defineModel<ChartType>({ default: ChartType.CANDLESTICK })

const currentType = computed(() => {
  return chartTypes.find(t => t.value === model.value) || chartTypes[0]!
})

// 添加一个非空断言确保模板中使用时不会报错
const currentLabel = computed(() => currentType.value!.label)
const currentIcon = computed(() => currentType.value!.icon)
</script>
