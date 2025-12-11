<template>
  <div class='row q-px-md radius-24 bg-dark-secondary full-height items-center'>
    <q-img :src='walletLogo' width='24px' height='24px' />
    <div class='q-ml-sm text-neutral'>{{ walletType }}</div>
    <div class='q-ml-sm text-light text-bold font-size-18'>{{ balance }}</div>
  </div>
</template>

<script setup lang='ts'>
import { constants } from 'src/constant'
import { user } from 'src/stores/export'
import { computed } from 'vue'

const walletType = computed(() => user.User.walletConnectedType())
const walletLogo = computed(() => walletType.value === user.WalletConnectType.Metamask ? constants.METAMASK_LOGO : constants.CHECKO_LOGO)
const balance = computed(() => user.User.balance())

</script>
