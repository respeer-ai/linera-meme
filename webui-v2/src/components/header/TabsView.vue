<template>
  <q-tabs
    v-model='tab'
    indicator-color='transparent'
  >
    <q-tab :name='Tab.Swap' :label='t("navigation.swap")' @click='onUpdateTab(Tab.Swap)' />
    <q-tab :name='Tab.Explore' :label='t("navigation.explore")' @click='onUpdateTab(Tab.Explore)' />
    <q-tab :name='Tab.Positions' :label='t("navigation.positions")' @click='onUpdateTab(Tab.Positions)' />
    <q-tab :name='Tab.Trending' :label='t("navigation.trending")' @click='onUpdateTab(Tab.Trending)' />
    <q-tab :name='Tab.Docs' :label='t("navigation.docs")' @click='onUpdateTab(Tab.Docs)' />
  </q-tabs>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

const tab = computed(() => {
  const matched = Object.entries(routers).find(([, path]) => path === route.path)
  return (matched?.[0] as Tab | undefined) || Tab.Swap
})

const onUpdateTab = (_tab: Tab) => {
  void router.push({ path: routers[_tab] })
}

</script>
