<template>
  <q-tabs
    v-model='tab'
    indicator-color='transparent'
  >
    <q-tab :name='Tab.Swap' :label='Tab.Swap' @click='onUpdateTab(Tab.Swap)' />
    <q-tab :name='Tab.Explore' :label='Tab.Explore' @click='onUpdateTab(Tab.Explore)' />
    <q-tab :name='Tab.Trending' :label='Tab.Trending' @click='onUpdateTab(Tab.Trending)' />
    <q-tab :name='Tab.Docs' :label='Tab.Docs' @click='onUpdateTab(Tab.Docs)' />
  </q-tabs>
</template>

<script setup lang='ts'>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

enum Tab {
  Swap = 'Swap',
  Explore = 'Explore',
  Trending = 'Trending',
  Docs = 'Docs'
}

const tab = ref(Tab.Swap)

const routers = ref<Record<string, string>>({
  [Tab.Swap]: '/swap',
  [Tab.Explore]: '/explore',
  [Tab.Trending]: '/trending',
  [Tab.Docs]: '/docs'
})

const router = useRouter()

const onUpdateTab = (_tab: Tab) => {
  void router.push({ path: routers.value[_tab] })
}

</script>
