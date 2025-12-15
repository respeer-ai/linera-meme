<template>
  <q-list class='text-light'>
    <q-item class='items-center' clickable @click='onSwitchWalletClick'>
      <q-icon name='swap_horiz' size='24px' />
      <div class='q-ml-sm'>
        Switch Wallet
      </div>
    </q-item>
    <q-item class='items-center' clickable @click='onDisconnectWalletClick' v-close-popup>
      <q-icon name='power_settings_new' size='24px' />
      <div class='q-ml-sm'>
        Disconnect
      </div>
    </q-item>
  </q-list>
  <q-dialog v-model='switchingWallet'>
    <div class='bg-dark-secondary q-py-lg radius-8' style='min-width: 400px;'>
      <connect-wallet-view @done='onConnectWalletDone' @error='switchingWallet = false' />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { user } from 'src/stores/export'

import ConnectWalletView from './ConnectWalletView.vue'

const switchingWallet = ref(false)

const emit = defineEmits<{
  (e: 'close-menu'): void
}>()

const onSwitchWalletClick = () => {
  switchingWallet.value = true
}

const onDisconnectWalletClick = () => {
  user.User.reset()
}

const onConnectWalletDone = () => {
  switchingWallet.value = false
  emit('close-menu')
}

</script>
