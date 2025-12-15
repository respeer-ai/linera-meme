<template>
  <div class='row q-px-md radius-24 bg-dark-secondary full-height items-center cursor-pointer'>
    <q-img :src='walletLogo' width='24px' height='24px' />
    <div class='q-ml-sm line-height-20'>
      <div class='text-neutral font-size-12'>{{ walletType }}</div>
      <div class='text-light text-bold'>{{ shortid.shortId(address, 6, 4).toUpperCase() }}</div>
    </div>
    <div v-if='!balanceUpdating' class='q-ml-sm text-orange text-bold font-size-18'>{{ balance }}</div>
    <span v-else>
      <q-spinner-hourglass
        color='neutral'
        size='1em'
        class='q-mb-xs'
      />
    </span>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { user } from 'src/stores/export'
import { shortid } from 'src/utils'
import { computed } from 'vue'

const walletType = computed(() => user.User.walletConnectedType())
const walletLogo = computed(() => walletType.value === user.WalletType.Metamask ? constants.METAMASK_LOGO : constants.CHECKO_LOGO)
const balance = computed(() => Number(user.User.balance()).toFixed(4))
const address = computed(() => user.User.publicKey())
const balanceUpdating = computed(() => user.User.balanceUpdating())

</script>
