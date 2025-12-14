<template>
  <div class='bg-primary-12 border-primary radius-16 row items-center q-px-md q-py-lg'>
    <q-icon name='info' size='24px' />
    <div class='q-ml-sm'>
      <div style='font-size: 18px;'>Connect your wallet to start creating . trading . mining tokens on Linera</div>
      <div class='text-neutral'>Supported wallets: Metamask with Linera Web Client, CheCko with MaaS</div>
    </div>
    <q-space />
    <connect-wallet-btn label='Connect Now' :show-icon='false' />
  </div>
</template>

<script setup lang='ts'>

import ConnectWalletBtn from './ConnectWalletBtn.vue'

</script>
