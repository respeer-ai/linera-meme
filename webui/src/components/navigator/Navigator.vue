<template>
  <div class='row items-center'>
    <div class='cursor-pointer'>
      <q-img
        :src='selectedIcon'
        height='36px'
        width='480px'
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
    </q-tabs>
    <q-btn
      flat label='create meme token' class='text-red-6 border-red-4' rounded
      @click='onCreateMemeTokenClick'
    />
    <ConnectWallet />
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

const tab = computed({
  get: () => path.value.includes('meme') ? 'meme' : path.value.includes('swap') ? 'swap' : 'blob',
  set: (v) => {
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
