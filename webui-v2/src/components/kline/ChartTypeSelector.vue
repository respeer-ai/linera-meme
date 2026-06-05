<template>
  <q-btn-dropdown
    :label="currentLabel"
    :icon="currentIcon"
    unelevated
    dense
    no-caps
    color="dark-secondary"
    text-color="neutral"
    dropdown-icon="expand_more"
    class="chart-toolbar-select chart-toolbar-select--chart-type radius-8"
  >
    <q-list dense class="bg-dark-secondary text-neutral">
      <q-item
        v-for="type in chartTypes"
        :key="type.value"
        clickable
        v-close-popup
        @click="model = type.value"
        :active="model === type.value"
        active-class="bg-primary text-white"
      >
        <q-item-section avatar>
          <q-icon :name="type.icon" size="20px" />
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ type.label }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChartType } from './ChartType'

const chartTypes = [
  { value: ChartType.CANDLESTICK, label: 'Candles', icon: 'candlestick_chart' },
  { value: ChartType.LINE, label: 'Line', icon: 'show_chart' },
  { value: ChartType.AREA, label: 'Area', icon: 'area_chart' },
]

const model = defineModel<ChartType>({ default: ChartType.CANDLESTICK })

const currentType = computed(() => {
  return chartTypes.find((t) => t.value === model.value) || chartTypes[0]!
})

const currentLabel = computed(() => currentType.value.label)
const currentIcon = computed(() => currentType.value.icon)
</script>

<style scoped lang="sass">
.chart-toolbar-select
  min-width: unset
  padding-left: 4px
  padding-right: 4px

  :deep(.q-btn__content)
    gap: 4px
    padding: 0

  :deep(.q-icon)
    font-size: 17px

  :deep(.q-btn-dropdown__arrow)
    margin-left: 0

.chart-toolbar-select--chart-type
  width: auto
</style>
