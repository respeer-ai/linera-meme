<template>
  <q-page class='row justify-center'>
    <div class='page-width'>
      <div v-if='!walletConnected' class='q-mt-lg'>
        <wallet-tip-view />
      </div>
      <div class='q-mt-lg'>
        <search-view />
      </div>
      <div class='q-mt-lg'>
        <protocol-info-view />
      </div>
      <div class='q-mt-lg'>
        <tokens-panel-view />
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { user } from 'src/stores/export'

import WalletTipView from 'src/components/wallet/WalletTipView.vue'
import SearchView from 'src/components/search/SearchView.vue'
import ProtocolInfoView from 'src/components/protocol/ProtocolInfoView.vue'
import TokensPanelView from 'src/components/tokens/TokensPanelView.vue'

const walletConnected = computed(() => user.User.walletConnected())

</script>
