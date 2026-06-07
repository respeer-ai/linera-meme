<template>
  <q-page class='row justify-center'>
    <main class='page-width' aria-label='Linera Meme Swap trading page'>
      <header class='seo-intro' aria-hidden='false'>
        <h1 class='seo-only q-ma-none'>MicroMeme: Linera Meme Swap</h1>
        <p class='seo-only q-ma-none'>
          Trade and discover Linera meme tokens with realtime charts, trending markets, minable meme
          launches, and fast microchain-based execution.
        </p>
      </header>
      <div class='q-my-xl' role='region' aria-label='Meme token swap interface'>
        <trade-view />
      </div>
      <swap-faq-section />
    </main>
  </q-page>
</template>

<script setup lang='ts'>
import { useRoute } from 'vue-router'
import SwapFaqSection from 'src/components/faq/SwapFaqSection.vue'
import TradeView from 'src/components/trade/TradeView.vue'
import { usePageSeo } from 'src/utils/seo'

const route = useRoute()

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Linera Meme Swap - Realtime Meme Token Trading on Linera',
  description:
    route.meta.seo?.description ||
    'Trade meme tokens on Linera with realtime pricing, microchain-based execution, live charts, and low-latency swap flows.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'Linera Meme',
    'Linera Meme Swap',
    'Linera token trading',
    'Linera microchains',
    'Meme token liquidity',
  ],
}))
</script>

<style scoped lang='sass'>
.seo-intro
  height: 0
  overflow: hidden

.seo-only
  position: absolute
  width: 1px
  height: 1px
  padding: 0
  margin: -1px
  overflow: hidden
  clip: rect(0, 0, 0, 0)
  white-space: nowrap
  border: 0
</style>
