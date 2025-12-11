<template>
  <div class='bg-transparent text-transparent'>|</div>
</template>

<script setup lang='ts'>
import { user } from 'src/stores/export'
import { onMounted } from 'vue'
import { getProviderState, walletReadyCall } from '../wallet/GetWalletInfo'

onMounted(() => {
  walletReadyCall(() => {
    getProviderState(window.linera || window.ethereum, window.linera ? user.WalletConnectType.CheCko : user.WalletConnectType.Metamask, () => {
      getProviderState(window.ethereum, user.WalletConnectType.Metamask)
    })
  })
})

</script>
