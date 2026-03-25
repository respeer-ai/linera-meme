<template>
  <q-btn-dropdown
    :label='currentInterval.label'
    unelevated
    dense
    no-caps
    color='dark-secondary'
    text-color='neutral'
    dropdown-icon='expand_more'
    class='radius-8'
    style='min-width: 80px;'
  >
    <q-list dense class='bg-dark-secondary text-neutral'>
      <q-item
        v-for='interval in intervals'
        :key='interval.value'
        clickable
        v-close-popup
        @click='model = interval.value'
        :active='model === interval.value'
        active-class='bg-primary text-white'
      >
        <q-item-section>
          <q-item-label>{{ interval.label }}</q-item-label>
        </q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { Interval } from 'src/stores/kline/const'

const intervals = [
  { label: '1分钟', value: Interval.ONE_MINUTE },
  { label: '5分钟', value: Interval.FIVE_MINUTE },
  { label: '10分钟', value: Interval.TEN_MINUTE },
  { label: '15分钟', value: Interval.FIFTEEN_MINUTE },
  { label: '1小时', value: Interval.ONE_HOUR },
  { label: '4小时', value: Interval.FOUR_HOUR },
  { label: '1天', value: Interval.ONE_DAY }
]

const model = defineModel<Interval>({ default: Interval.ONE_MINUTE })

const currentInterval = computed(() => {
  return intervals.find(i => i.value === model.value) || intervals[0]!
})
</script>
