<template>
  <q-tabs
    v-model='tab'
    indicator-color='transparent'
  >
    <q-tab :name='Tab.Swap' :label='Tab.Swap' />
    <q-tab :name='Tab.Tokens' :label='Tab.Tokens' />
    <q-tab :name='Tab.Liquidity' :label='Tab.Liquidity' />
    <q-tab :name='Tab.Trending' :label='Tab.Trending' />
    <q-tab :name='Tab.Docs' :label='Tab.Docs' />
  </q-tabs>
</template>

<script setup lang='ts'>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'

enum Tab {
  Swap = 'Swap',
  Tokens = 'Tokens',
  Liquidity = 'Liquidity',
  Trending = 'Trending',
  Docs = 'Docs'
}

const tab = ref(Tab.Swap)

const routers = ref<Record<string, string>>({
  [Tab.Swap]: '/swap',
  [Tab.Tokens]: '/tokens',
  [Tab.Liquidity]: '/liquidity',
  [Tab.Trending]: '/trending',
  [Tab.Docs]: '/docs'
})

const router = useRouter()

watch(tab, () => {
  void router.push({ path: routers.value[tab.value] })
})

</script>
