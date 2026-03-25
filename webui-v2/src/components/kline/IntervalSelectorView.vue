<template>
  <div class='row q-gutter-xs'>
    <q-btn
      v-for='option in intervalOptions'
      :key='option.value'
      :label='option.label'
      :outline='model !== option.value'
      :unelevated='model === option.value'
      :color='model === option.value ? "primary" : "neutral"'
      :text-color='model === option.value ? "white" : "neutral"'
      dense
      no-caps
      class='radius-8'
      style='min-width: 48px; font-size: 12px; font-weight: 500;'
      @click='model = option.value'
    />
  </div>
</template>

<script setup lang='ts'>
import { Interval } from 'src/stores/kline/const'

const intervalOptions = [
  { label: '1m', value: Interval.ONE_MINUTE },
  { label: '5m', value: Interval.FIVE_MINUTE },
  { label: '15m', value: Interval.TEN_MINUTE },
  { label: '1h', value: Interval.ONE_HOUR },
  { label: '1d', value: Interval.ONE_DAY }
]

const model = defineModel<Interval>({ default: Interval.ONE_MINUTE })
</script>
