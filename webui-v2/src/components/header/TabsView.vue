<template>
  <q-tabs
    v-model='tab'
    indicator-color='transparent'
  >
    <q-tab :name='Tab.Swap' :label='Tab.Swap' @click='onUpdateTab(Tab.Swap)' />
    <q-tab :name='Tab.Explore' :label='Tab.Explore' @click='onUpdateTab(Tab.Explore)' />
    <q-tab :name='Tab.Positions' :label='Tab.Positions' @click='onUpdateTab(Tab.Positions)' />
    <q-tab :name='Tab.Trending' :label='Tab.Trending' @click='onUpdateTab(Tab.Trending)' />
    <q-tab :name='Tab.Docs' :label='Tab.Docs' @click='onUpdateTab(Tab.Docs)' />
  </q-tabs>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

enum Tab {
  Swap = 'Swap',
  Explore = 'Explore',
  Positions = 'Positions',
  Trending = 'Trending',
  Docs = 'Docs'
}

const routers: Record<string, string> = {
  [Tab.Swap]: '/',
  [Tab.Explore]: '/explore',
  [Tab.Positions]: '/positions',
  [Tab.Trending]: '/trending',
  [Tab.Docs]: '/docs'
}

const router = useRouter()
const route = useRoute()

const tab = computed(() => {
  const matched = Object.entries(routers).find(([, path]) => path === route.path)
  return (matched?.[0] as Tab | undefined) || Tab.Swap
})

const onUpdateTab = (_tab: Tab) => {
  void router.push({ path: routers[_tab] })
}

</script>
