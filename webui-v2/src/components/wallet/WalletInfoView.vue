<template>
  <div class='row q-px-md radius-24 bg-dark-secondary full-height items-center cursor-pointer hover-primary-direct'  @click='onWalletInfoClick'>
    <q-img :src='walletLogo' width='24px' height='24px' />
    <div class='q-ml-sm line-height-20'>
      <div class='text-neutral font-size-12'>{{ walletType }}</div>
      <div class='text-light text-bold'>{{ shortid.shortId(address, 6, 4).toUpperCase() }}</div>
    </div>
    <div v-if='!balanceUpdating' class='q-ml-sm text-orange text-bold font-size-18'>{{ balance }}</div>
    <span v-else class='q-ml-sm'>
      <q-spinner-hourglass
        color='neutral'
        size='1em'
      />
    </span>
  </div>
  <q-dialog v-model='menuOpen' position='right' full-height>
    <div style='min-width: 400px;' class='bg-dark-secondary q-pa-lg radius-8'>
      <wallet-info-menu-view />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { user } from 'src/stores/export'
import { shortid } from 'src/utils'
import { computed, ref } from 'vue'

import WalletInfoMenuView from './WalletInfoMenuView.vue'

const walletType = computed(() => user.User.walletConnectedType())
const walletLogo = computed(() => walletType.value === user.WalletType.Metamask ? constants.METAMASK_LOGO : constants.CHECKO_LOGO)
const balance = computed(() => Number(user.User.balance()).toFixed(4))
const address = computed(() => user.User.publicKey())
const balanceUpdating = computed(() => user.User.balanceUpdating())

const menuOpen = ref(false)

const onWalletInfoClick = () => {
  menuOpen.value = true
}

</script>
