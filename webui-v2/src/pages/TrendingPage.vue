<template>
  <q-page class='row justify-center'>
    <div class='page-width'>
      <div class='q-mt-xl'>
        <trending-view />
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { useRoute } from 'vue-router'
import TrendingView from 'src/components/trending/TrendingView.vue'
import { usePageSeo } from 'src/utils/seo'

const route = useRoute()

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Trending Linera Meme Tokens - Realtime Movers, Volume, and New Launches',
  description:
    route.meta.seo?.description ||
    'Track trending Linera meme tokens with realtime gainers, volume leaders, and new token launches across the Linera ecosystem.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'Linera Meme',
    'trending Linera tokens',
    'Linera volume',
    'Linera realtime trading',
  ],
}))
</script>
