<template>
  <q-btn-dropdown
    :label="currentInterval.label"
    icon="schedule"
    unelevated
    dense
    no-caps
    color="dark-secondary"
    text-color="neutral"
    dropdown-icon="expand_more"
    class="chart-toolbar-select chart-toolbar-select--interval radius-8"
  >
    <q-list dense class="bg-dark-secondary text-neutral">
      <q-item
        v-for="interval in intervals"
        :key="interval.value"
        clickable
        v-close-popup
        @click="model = interval.value"
        :active="model === interval.value"
        active-class="bg-primary text-white"
      >
        <q-item-section>
          <q-item-label>{{ interval.label }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Interval } from 'src/stores/kline/const'

const intervals = [
  { label: '1m', value: Interval.ONE_MINUTE },
  { label: '5m', value: Interval.FIVE_MINUTE },
  { label: '10m', value: Interval.TEN_MINUTE },
  { label: '15m', value: Interval.FIFTEEN_MINUTE },
  { label: '1h', value: Interval.ONE_HOUR },
  { label: '4h', value: Interval.FOUR_HOUR },
  { label: '1D', value: Interval.ONE_DAY },
]

const model = defineModel<Interval>({ default: Interval.ONE_MINUTE })

const currentInterval = computed(() => {
  return intervals.find((i) => i.value === model.value) || intervals[0]!
})
</script>

<style scoped lang="sass">
.chart-toolbar-select
  min-width: unset
  padding-left: 4px
  padding-right: 4px

  :deep(.q-btn__content)
    gap: 3px
    padding: 0

  :deep(.q-icon)
    font-size: 17px

  :deep(.q-btn-dropdown__arrow)
    margin-left: 0

.chart-toolbar-select--interval
  width: auto
</style>
