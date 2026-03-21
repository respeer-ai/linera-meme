<template>
  <q-page class='row justify-center'>
    <div class='page-width'>
      <div class='q-mt-lg'>
        <protocol-info-view />
      </div>
      <div class='q-mt-lg'>
        <tokens-panel-view :tab='Tab.Tokens' />
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { Tab } from 'src/components/tokens/Tab'

import ProtocolInfoView from 'src/components/protocol/ProtocolInfoView.vue'
import TokensPanelView from 'src/components/tokens/TokensPanelView.vue'

</script>
