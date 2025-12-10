<template> 
  <div class='row q-header-line'>
    <div class='cursor-pointer row'>
      <div class='bg-primary-25 hover-primary radius-8 flex justify-center items-center' style='width: 48px; height: 48px;'>
        <q-img :src='laughPng' width='36px' height='36px' />
      </div>
      <div class='q-ml-sm'>
        <div class='text-light text-h5 text-bold text-gradient-primary-secondary'> {{ productName }} </div>
        <div class='text-xs text-neutral' style='line-height: 1em;'>Creating . Trading . Mining Meme on Linera</div>
      </div>
    </div>
    <div class='q-ml-lg'>
      <tabs-view />
    </div>
    <q-space />
    <div>
      <network-view />
    </div>
    <div class='q-ml-md'>
      <connect-wallet-view />
    </div>
    <div class='header-actions q-ml-md'>
      <q-btn fab flat round icon='invert_colors' size='24px' class='bg-dark-dark' @click='onModeSwitchClick' />
    </div>
  </div>
</template>

<script lang='ts' setup>
import { Dark } from 'quasar'

import { laughPng } from 'src/assets'

import TabsView from './TabsView.vue'
import NetworkView from './NetworkView.vue'
import ConnectWalletView from './ConnectWalletView.vue'

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
