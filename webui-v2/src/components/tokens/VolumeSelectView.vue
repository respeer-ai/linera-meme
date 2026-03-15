<template>
  <q-select
    v-model='model'
    :options='options'
    option-label='label'
    option-value='value'
    emit-value
    map-options
    borderless
    popup-content-class='text-white radius-12 shadow-2'
    class='bg-transparent text-white radius-12 q-px-sm border-neutral-25'
  />
</template>

<script setup lang='ts'>
import { kline } from 'src/stores/export';


const options = [
  { label: '1H volume', value: kline.TickerInterval.OneHour },
  { label: '1D volume', value: kline.TickerInterval.OneDay },
  { label: '1W volume', value: kline.TickerInterval.OneWeek },
  { label: '1M volume', value: kline.TickerInterval.OneMonth },
  { label: '1Y volume', value: kline.TickerInterval.OneYear },
  { label: 'All time volume', value: kline.TickerInterval.All }
]

const model = defineModel({ default: kline.TickerInterval.OneDay })
</script>

<style scoped lang="sass">

::v-deep(.q-field__inner)
  .q-field--dark,
  .q-field--light,
  .q-field--filled,
  .q-field__control
    background-color: transparent
  .q-field__native
    color: var(--q-neutral) !important
    font-weight: bold
    background-color: transparent !important
  .q-field__control,
  .q-field__native,
  .q-field__marginal
    min-height: 40px
    height: 40px
  .q-field__suffix,
  .q-field__prepend
    line-height: 32px
  .q-field__control:hover
    background-color: transparent !important

</style>