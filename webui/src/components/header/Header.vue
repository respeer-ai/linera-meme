<template>
  <div class='row items-center'>
    <div class='cursor-pointer' @click='onLogoClick'>
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
      <q-tab v-if='false' name='campaign' label='campaign' />
    </q-tabs>
    <ConnectWallet />
    <q-btn
      flat label='Create meme token' class='text-red-6 border-red-4' rounded
      @click='onCreateMemeTokenClick'
    />
  </div>
</template>

<script setup lang='ts'>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { graphqlResult } from 'src/utils'
import { block, user, kline, proxy, ams } from 'src/localstore'

import { blobGatewayLogo, lineraMemeLogo, lineraSwapLogo } from 'src/assets'

import ConnectWallet from './ConnectWallet.vue'

const route = useRoute()
const router = useRouter()
const path = computed(() => route.path)

const _block = block.useBlockStore()
const _user = user.useUserStore()
const _kline = kline.useKlineStore()
const _proxy = proxy.useProxyStore()
const _ams = ams.useAmsStore()

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

const goHome = () => {
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
}

const onLogoClick = () => {
  goHome()
}

onMounted(() => {
  _kline.initializeKline()
  _proxy.initializeProxy()
  _ams.initializeProxy()
  goHome()
})

const subscriptionId = ref(undefined as unknown as string)

const subscriptionHandler = (msg: unknown) => {
  const data = (graphqlResult.keyValue(msg, 'data') || []) as Record<string, Record<string, Record<string, Record<string, Record<string, unknown>>>>>
  if (data.result.notifications.reason.NewBlock) {
    const blockChainId = data.result.notifications.chain_id.toString()
    if (blockChainId === _user.chainId) {
      _block.blockHeight = data.result.notifications.reason.NewBlock.height as number
      _block.blockHash = data.result.notifications.reason.NewBlock.hash as string
    }
  }
}

onMounted(() => {
  if (subscriptionId.value) return
  window.linera?.request({
    method: 'linera_subscribe'
  }).then((_subscriptionId) => {
    subscriptionId.value = _subscriptionId as string
    window.linera.on('message', subscriptionHandler)
  }).catch((e) => {
    console.log('Fail subscribe', e)
  })
})

onUnmounted(() => {
  if (!subscriptionId.value) return
  void window.linera?.request({
    method: 'linera_unsubscribe',
    params: [subscriptionId.value]
  })
  subscriptionId.value = undefined as unknown as string
})

</script>

<style scoped lang='sass'>
</style>
