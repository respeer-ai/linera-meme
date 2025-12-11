<template>
  <div class='row content-start wrap'>
    <div class='trade-action'>
      <div class='row items-center'>
        <token-input-view :action='TokenAction.Sell' style='width: calc(50% - 4px);' v-model='sellToken' :tokens='sellTokens' v-model:amount='sellAmount' />
        <div class='radius-24 bg-accent q-pa-sm cursor-pointer hover-primary' style='height: 48px; width: 48px; margin-left: -20px; z-index: 1000;' @click='onSwitchTokenClick'>
          <q-icon name='arrow_forward' size='32px' />
        </div>
        <token-input-view :action='TokenAction.Buy' style='width: calc(50% - 4px); margin-left: -20px;' :auto-focus='false' v-model='buyToken' :tokens='buyTokens' v-model:amount='buyAmount' />
      </div>
      <div class='row q-mt-sm font-size-12 text-neutral cursor-pointer'>
        <div>1 {{ sellToken?.meme?.ticker }} = 0.00000123455 {{ buyToken?.meme?.ticker }}</div>
        <q-space />
        <q-icon name='local_gas_station' size='18px' />
        <div class='q-ml-xs'>0.00000001234</div>
        <div class='q-ml-xs'>
          <q-icon name='keyboard_arrow_down' size='18px' />
        </div>
      </div>
      <q-btn no-caps rounded class='fill-parent-width bg-primary q-mt-sm' :loading='checkingPrice' :disabled='btnActions[0]?.disable'>
        <template #loading>
          <q-spinner-hourglass class="on-left" />
          {{ btnActions[0]?.label }}
        </template>
        {{ btnActions[0]?.label }}
      </q-btn>
      <q-card flat class='q-mt-md radius-8' style='overflow: hidden;'>
        <price-chart-view height='440px' />
      </q-card>
    </div>

    <q-card flat class='flex-grow selected-token-info border-dark-secondary radius-8 bg-dark-secondary'>
      <TokenInfoView :token='buyToken' />
    </q-card>
  </div>
</template>

<script setup lang='ts'>
import { TokenAction } from './TokenAction'
import { Token } from './Token'
import { computed, onMounted, ref, watch } from 'vue'
import { ams, meme, swap } from 'src/stores/export'
import { constants } from 'src/constant'

import TokenInputView from './TokenInputView.vue'
import TokenInfoView from './TokenInfoView.vue'
import PriceChartView from '../kline/PriceChartView.vue'

const tokens = computed(() => ams.applications().map((el) => {
  return {
    ...el,
    meme: JSON.parse(el.spec) as meme.Meme
  }
}))
const pools = computed(() => swap.pools())
const buyToken = ref(undefined as unknown as Token)
const buyTokenId = computed(() => buyToken.value?.applicationId || constants.LINERA_NATIVE_ID)
const buyAmount = ref('')
const buyTokens = computed(() => tokens.value.filter((el) => {
  return pools.value.findIndex((_el) => {
    return (el.applicationId === _el.token1 && _el.token0 === sellTokenId.value) ||
           (el.applicationId === _el.token0 && _el.token1 === sellTokenId.value)
  }) >= 0
}))
const sellToken = ref(undefined as unknown as Token)
const sellTokenId = computed(() => sellToken.value?.applicationId || constants.LINERA_NATIVE_ID)
const sellAmount = ref('')
const sellTokens = computed(() => tokens.value.filter((el) => {
  return pools.value.findIndex((_el) => {
    return (el.applicationId === _el.token1 && _el.token0 === buyTokenId.value) ||
           (el.applicationId === _el.token0 && _el.token1 === buyTokenId.value)
  }) >= 0
}))
const pool = computed(() =>pools.value.find((el) => {
  return (el.token0 === buyTokenId.value && el.token1 === sellTokenId.value) ||
         (el.token1 === buyTokenId.value && el.token0 === sellTokenId.value)
}))

watch(sellAmount, () => {
  const price = Number((sellToken.value?.applicationId === pool.value?.token0 ? pool.value?.token0Price : pool.value?.token1Price) as string)
  setTimeout(() => {
    buyAmount.value = ((Number(sellAmount.value) * price) || 0).toFixed(4)
  }, 1000)
})

watch(buyAmount, () => {
  const price = Number((buyToken.value?.applicationId === pool.value?.token1 ? pool.value?.token1Price : pool.value?.token0Price) as string)
  setTimeout(() => {
    sellAmount.value = ((Number(buyAmount.value) * price) || 0).toFixed(4)
  }, 1000)
})

const checkingPrice = ref(false)

interface BtnActionItem {
  label: string
  disable: boolean
}

enum BtnAction {
  InputAmount = 'Input amount',
  CheckingPrice = 'Checking price',
  Review = 'Review',
  Swap = 'Swap'
}

const btnActions = ref([{
  label: BtnAction.InputAmount,
  disable: true
}, {
  label: BtnAction.CheckingPrice,
  disable: true
}, {
  label: BtnAction.Review,
  disable: true
}, {
  label: BtnAction.Swap,
  disable: false
}] as BtnActionItem[])

const onSwitchTokenClick = () => {
  const token = buyToken.value
  buyToken.value = sellToken.value
  sellToken.value = token
}

onMounted(() => {
  swap.getPools(() => {
    ams.getApplications(undefined, () => {
      buyToken.value = tokens.value[0] as Token
    })
  })
})

</script>

<style scoped lang='sass'>
.trade-action
  width: 840px

.selected-token-info
  width: calc(100% - 840px - 16px)
  margin-left: 16px

@media (max-width: 960px)
  .trade-action
    width: 100%

  .selected-token-info
    width: 100%
    margin-left: 0
    margin-top: 16px
</style>