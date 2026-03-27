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
import { useRoute } from 'vue-router'
import { Tab } from 'src/components/tokens/Tab'
import { usePageSeo } from 'src/utils/seo'

import ProtocolInfoView from 'src/components/protocol/ProtocolInfoView.vue'
import TokensPanelView from 'src/components/tokens/TokensPanelView.vue'

const route = useRoute()

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Explore Linera Meme Tokens, Pools, and Microchain Markets',
  description:
    route.meta.seo?.description ||
    'Explore Linera meme tokens, liquidity pools, token stats, and microchain market activity in one realtime dashboard.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'Linera Meme',
    'Linera token explorer',
    'Linera pools',
    'Linera microchain',
  ],
}))
</script>
