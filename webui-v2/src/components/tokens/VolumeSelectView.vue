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
import { ref } from 'vue'

const options = [
  { label: '1H volume', value: '1h' },
  { label: '1D volume', value: '1d' },
  { label: '1W volume', value: '1w' },
  { label: '1M volume', value: '1m' },
  { label: '1Y volume', value: '1y' },
  { label: 'All time volume', value: 'all' }
]

const model = ref('1d')
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