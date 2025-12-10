<template> 
  <div class='row q-header-line'>
    <div class='cursor-pointer row'>
      <div class='bg-primary-25 hover-primary radius-8 flex justify-center items-center' style='width: 48px; height: 48px;'>
        <q-img :src='laughPng' width='36px' height='36px' />
      </div>
      <q-toolbar-title class='text-light text-h4 text-bold text-gradient-primary-secondary q-header-line'> {{ productName }} </q-toolbar-title>
    </div>
    <q-space />
    <div class='header-actions'>
      <q-btn fab flat round icon='invert_colors' size='24px' class='bg-dark-dark' @click='onModeSwitchClick' />
    </div>
  </div>
</template>

<script lang='ts' setup>
import { Dark } from 'quasar'

import { laughPng } from 'src/assets'

const productName = import.meta.env.VITE_PRODUCT_NAME || import.meta.env.PRODUCT_NAME

const onModeSwitchClick = () => {
  Dark.toggle()
}

</script>

<style scoped lang='sass'>
.header-actions
  ::v-deep(.q-btn--fab .q-icon)
    font-size: 32px
</style>
