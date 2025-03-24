<template>
  <div class='row items-center'>
    <div class='cursor-pointer'>
      <q-img
        :src='selectedIcon'
        height='36px'
        width='240px'
        fit='contain'
        position='0 0'
      />
    </div>
    <q-space />
    <q-tabs
      v-model='tab'
      class='text-black horizontal-inner-x-margin-right'
      narrow-indicator
      dense indicator-color='red-6'
    >
      <q-tab name='meme' label='meme' />
      <q-tab name='swap' label='swap' />
      <q-tab name='blob' label='blob' />
      <q-tab name='campaign' label='campaign' />
    </q-tabs>
    <ConnectWallet />
    <q-btn
      flat label='Create meme token' class='text-red-6 border-red-4' rounded
      @click='onCreateMemeTokenClick'
    />
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { host } from 'src/mystore'

import { blobGatewayLogo, lineraMemeLogo, lineraSwapLogo } from 'src/assets'

import ConnectWallet from './ConnectWallet.vue'

const route = useRoute()
const router = useRouter()
const path = computed(() => route.path)

const path2tab = () => {
  if (path.value.includes('meme')) return 'meme'
  if (path.value.includes('swap')) return 'swap'
  if (path.value.includes('blob')) return 'blob'
  if (path.value.includes('campaign')) return 'campaign'
}

const tab = computed({
  get: () => path2tab(),
  set: (v: string) => {
    void router.push({ path: '/' + v })
  }
})
const selectedIcon = ref(lineraMemeLogo)

const onCreateMemeTokenClick = () => {
  void router.push({ path: '/create/meme' })
}

const _host = host.useHostStore()

onMounted(() => {
  _host.windowHost = window.location.host

  if (window.location.protocol.startsWith('https')) {
    _host.apiSchema = 'https'
  }

  if (window.location.hostname.endsWith('linerameme.fun')) {
    selectedIcon.value = lineraMemeLogo
    void router.push({ path: window.location.pathname === '/' ? '/meme' : window.location.pathname })
  } else if (window.location.hostname.endsWith('lineraswap.fun')) {
    selectedIcon.value = lineraSwapLogo
    void router.push({ path: window.location.pathname === '/' ? '/swap' : window.location.pathname })
  } else if (window.location.hostname.endsWith('blobgateway.com')) {
    selectedIcon.value = blobGatewayLogo
    void router.push({ path: window.location.pathname === '/' ? '/blob' : window.location.pathname })
  } else {
    selectedIcon.value = lineraMemeLogo
    void router.push({ path: window.location.pathname === '/' ? '/meme' : window.location.pathname })
  }
})

</script>

<style scoped lang='sass'>
</style>
