<template>
  <q-list class='text-light'>
    <q-item class='items-center' clickable @click='onSwitchWalletClick' v-close-popup>
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
      <connect-wallet-view @done='switchingWallet = false' @error='switchingWallet = false' />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { Cookies } from 'quasar'
import { user } from 'src/stores/export'

import ConnectWalletView from './ConnectWalletView.vue'

const switchingWallet = ref(false)

const onSwitchWalletClick = () => {
  switchingWallet.value = true
}

const onDisconnectWalletClick = () => {
  Cookies.remove(user.WalletCookie.WalletConnectType)
}

</script>
