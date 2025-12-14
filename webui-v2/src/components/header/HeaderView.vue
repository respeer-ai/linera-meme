<template> 
  <div class='row q-header-line'>
    <logo-view />
    <div class='q-ml-lg'>
      <tabs-view />
    </div>
    <q-space />
    <subscription-view />
    <div class='q-ml-md'>
      <network-view />
    </div>
    <div v-if='walletConnected && walletType === user.WalletType.CheCko' class='q-ml-md'>
      <create-meme-btn />
    </div>
    <div v-if='!walletConnected' class='q-ml-md'>
      <connect-wallet-btn />
    </div>
    <div v-if='walletConnected' class='q-ml-md'>
      <wallet-info-view />
    </div>
    <div class='header-actions q-ml-md'>
      <q-btn fab flat round icon='invert_colors' size='24px' class='bg-dark-dark' @click='onModeSwitchClick' />
    </div>
  </div>
</template>

<script lang='ts' setup>
import { Dark } from 'quasar'
import { computed } from 'vue'
import { user } from 'src/stores/export'

import TabsView from './TabsView.vue'
import NetworkView from './NetworkView.vue'
import ConnectWalletBtn from '../wallet/ConnectWalletBtn.vue'
import LogoView from '../logo/LogoView.vue'
import CreateMemeBtn from '../meme/CreateMemeBtn.vue'
import WalletInfoView from '../wallet/WalletInfoView.vue'
import SubscriptionView from '../subscription/SubscriptionView.vue'

const walletConnected = computed(() => user.User.walletConnected())
const walletType = computed(() => user.User.walletConnectedType())

const onModeSwitchClick = () => {
  Dark.toggle()
}

</script>

<style scoped lang='sass'>
.header-actions
  ::v-deep(.q-btn--fab .q-icon)
    font-size: 32px
</style>
