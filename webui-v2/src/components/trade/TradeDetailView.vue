<template>
  <div>
    <!-- TODO: use fee ratio from pool -->
    <token-info-line-view label='Fee (0.3%)' :logo='sellTokenLogo' :value='fee + " ($ 0)"' value-color='light' :value-bold='false' :underline='false' />
    <div class='q-mt-sm'>
      <token-info-line-view label='Network Fee' :logo='constants.LINERA_LOGO' :value='networkFeeAmount + " ($ 0)"' value-color='light' :value-bold='false' :underline='false' />
    </div>
    <div v-if='expanded' class='q-mt-sm'>
      <token-info-line-view label='Price' :value='`1 ${sellTokenTicker} = ${sellPrice} ${buyTokenTicker}`' value-color='light' :value-bold='false' :underline='false' />
    </div>
    <div v-if='expanded'  class='q-mt-sm'>
      <token-info-line-view label='Slippage' :value='slippage + "%"' value-color='neutral' :value-bold='false' :underline='false' />
    </div>
    <div v-if='expanded'  class='q-mt-sm'>
      <token-info-line-view label='Order Router' :logo='constants.MICROMEME_LOGO' value='MicroMeme Proxy' value-color='light' :value-bold='false' :underline='false' />
    </div>
    <div v-if='expanded' class='q-mt-sm'>
      <token-info-line-view label='Price Impact' :value='priceImpactPercent + "%"' value-color='neutral' :value-bold='false' :underline='false' />
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, toRef } from 'vue'
import { Token } from './Token'
import { constants } from 'src/constant'
import { ams } from 'src/stores/export'

import TokenInfoLineView from './TokenInfoLineView.vue'

interface Props {
  sellToken: Token
  sellAmount: string
  buyToken: Token
  buyAmount: string
  sellPrice: string
  slippage: number
  priceImpact: string
  expanded: boolean
  networkFeeAmount: string
}
const props = defineProps<Props>()
const sellToken = toRef(props, 'sellToken')
const sellAmount = toRef(props, 'sellAmount')
const buyToken = toRef(props, 'buyToken')
const sellPrice = toRef(props, 'sellPrice')
const expanded = toRef(props, 'expanded')
const slippage = toRef(props, 'slippage')
const priceImpact = toRef(props, 'priceImpact')
const networkFeeAmount = toRef(props, 'networkFeeAmount')

const priceImpactPercent = computed(() => (Number(priceImpact.value) * 100).toFixed(4))
const fee = computed(() => Number(sellAmount.value) * 0.003)

const sellTokenTicker = computed(() => sellToken.value?.meme?.ticker || constants.LINERA_TICKER)
const buyTokenTicker = computed(() => buyToken.value?.meme?.ticker || constants.LINERA_TICKER)
const sellTokenLogo = computed(() => ams.Ams.applicationLogo(sellToken.value) || constants.LINERA_LOGO)

</script>
