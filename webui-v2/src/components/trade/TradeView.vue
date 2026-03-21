<template>
  <div>
    <div class='row'>
      <q-card flat class='radius-8' style='overflow: hidden; min-width: 560px; width: calc(100% - 480px - 16px);'>
        <price-chart-view height='640px' />
      </q-card>
      <q-space />
      <div style='width: 480px;'>
        <div class='items-center'>
          <token-input-view :action='TokenAction.Sell' v-model='sellToken' :tokens='sellTokens' v-model:amount='sellAmount' :disable='!walletConnected' />
          <div class='row'>
            <q-space />
            <div class='radius-24 bg-accent q-pa-sm cursor-pointer hover-primary' style='height: 48px; width: 48px; margin-top: -20px; z-index: 1000;' @click='onSwitchTokenClick'>
              <q-icon name='arrow_downward' size='32px' />
            </div>
            <q-space />
          </div>
          <token-input-view :action='TokenAction.Buy' style='margin-top: -20px;' :auto-focus='false' v-model='buyToken' :tokens='buyTokens' v-model:amount='buyAmount' :disable='!walletConnected' />
        </div>
        <q-btn no-caps rounded class='fill-parent-width bg-primary q-mt-sm font-size-20' :disabled='btnActions[btnStep]?.disable' @click='onSwapClick'>
          <template #loading>
            <q-spinner-hourglass class="on-left" />
            {{ btnActions[btnStep]?.label }}
          </template>
          {{ btnActions[btnStep]?.label }}
        </q-btn>
        <div class='row q-mt-md font-size-14 text-neutral'>
          <div>1 {{ sellTokenTicker }} = {{ sellPrice }} {{ buyTokenTicker }}</div>
          <q-space />
          <div class='bg-accent q-px-sm radius-8 text-bold border-secondary-25 cursor-pointer hover-primary' @click='onSetSlippageClick'>
            <div class='text-neutral'>
              {{ slippage }}%
            </div>
          </div>
          <div class='row q-ml-xs cursor-pointer hover-primary' @click='onShowTradeInfoClick'>
            <div>
              <q-icon name='local_gas_station' size='18px' />
            </div>
            <div class='q-ml-xs text-neutral'>{{ swapGasAmount }}</div>
            <div class='q-ml-xs'>
              <q-icon name='keyboard_arrow_down' size='18px' />
            </div>
          </div>
          <div v-if='showingTradeInfo' class='q-mt-lg full-width'>
            <trade-detail-view
              :buy-token='buyToken'
              :sell-token='sellToken'
              :buy-amount='buyAmount'
              :sell-amount='sellAmount'
              :sell-price='sellPrice'
              :slippage='slippage'
              :price-impact='priceImpact'
              :expanded='true'
            />
          </div>
        </div>
      </div>
    </div>
  </div>
  <q-dialog v-model='reviewing' persistent>
    <div class='bg-dark-secondary q-py-lg radius-16 border-bottom-primary-twelve' style='min-width: 400px;'>
      <trade-info-view
        :buy-token='buyToken'
        :sell-token='sellToken'
        :buy-amount='buyAmount'
        :sell-amount='sellAmount'
        :sell-price='sellPrice'
        :slippage='slippage'
        :price-impact='priceImpact'
        @done='onSwapDone'
        @error='onSwapError'
        @cancel='onSwapCanceled'
      />
    </div>
  </q-dialog>
  <q-dialog v-model='settingSlippage'>
    <div class='bg-dark-secondary q-py-lg radius-16 border-bottom-primary-twelve' style='min-width: 400px;'>
      <set-slippage-view @done='onSetSlippageDone' @cancel='onSetSlippageCanceled' v-model='slippage' />
    </div>
  </q-dialog>
</template>

<script setup lang='ts'>
import { TokenAction } from './TokenAction'
import { Token } from './Token'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ams, meme, swap, user, notify } from 'src/stores/export'
import { constants } from 'src/constant'
import { defaultSlippage } from './Slippages'

import TokenInputView from './TokenInputView.vue'
import PriceChartView from '../kline/PriceChartView.vue'
import TradeInfoView from './TradeInfoView.vue'
import SetSlippageView from './SetSlippageView.vue'
import TradeDetailView from './TradeDetailView.vue'
import { Wallet } from 'src/wallet'

const walletConnected = computed(() => user.User.walletConnected())

const tokens = computed(() => ams.Ams.applications().map((el) => {
  return {
    ...el,
    meme: JSON.parse(el.spec) as meme.Meme
  }
}))
const pools = computed(() => swap.Swap.pools())

const buyToken = ref(undefined as unknown as Token)
const buyTokenId = computed(() => buyToken.value?.applicationId || constants.LINERA_NATIVE_ID)
const buyTokenTicker = computed(() => buyToken.value?.meme?.ticker || constants.LINERA_TICKER)
const buyAmount = ref('')
const buyTokens = computed(() => tokens.value.filter((el) => {
  return pools.value.findIndex((_el) => {
    return (el.applicationId === _el.token1 && _el.token0 === sellTokenId.value) ||
           (el.applicationId === _el.token0 && _el.token1 === sellTokenId.value)
  }) >= 0
}))

watch(buyTokenId, () => {
  swap.Swap.setBuyToken(buyTokenId.value)
}, {
  immediate: true
})

const reviewing = ref(false)
const settingSlippage = ref(false)
const slippage = ref(defaultSlippage)
const showingTradeInfo = ref(false)

watch(tokens, () => {
  if (buyToken.value === undefined && sellToken.value === undefined) {
    buyToken.value = tokens.value[0] as Token
  }
})

const sellToken = ref(undefined as unknown as Token)
const sellTokenId = computed(() => sellToken.value?.applicationId || constants.LINERA_NATIVE_ID)
const sellTokenTicker = computed(() => sellToken.value?.meme?.ticker || constants.LINERA_TICKER)
const sellAmount = ref('0.01')
const sellTokens = computed(() => tokens.value.filter((el) => {
  return pools.value.findIndex((_el) => {
    return (el.applicationId === _el.token1 && _el.token0 === buyTokenId.value) ||
           (el.applicationId === _el.token0 && _el.token1 === buyTokenId.value)
  }) >= 0
}))

watch(sellTokenId, () => {
  swap.Swap.setSellToken(sellTokenId.value)
}, {
  immediate: true
})

const pool = computed(() => swap.Swap.selectedPool())
const fullPrecisionSellPrice = computed(() => (Number(sellTokenId.value === pool.value?.token0 ? pool.value?.token0Price : pool.value?.token1Price) || 0))
const sellPrice = computed(() => fullPrecisionSellPrice.value.toFixed(6))
const priceImpact = computed(() => swap.Swap.calculatePriceImpact(buyTokenId.value, sellTokenId.value, sellAmount.value))

watch(sellAmount, () => {
  const price = Number((sellTokenId.value === pool.value?.token0 ? pool.value?.token0Price : pool.value?.token1Price) as string)
  setTimeout(() => {
    buyAmount.value = ((Number(sellAmount.value) * price) || (buyTokenId.value === constants.LINERA_NATIVE_ID ? 0.01 : 25)).toFixed(6)
    if (btnStep.value === 0 && Number(buyAmount.value) > 0 && Number(sellAmount.value) > 0) {
      btnStep.value += 1
    }
  }, 1000)
})

watch(buyAmount, () => {
  const price = Number((buyTokenId.value === pool.value?.token1 ? pool.value?.token1Price : pool.value?.token0Price) as string)
  setTimeout(() => {
    sellAmount.value = ((Number(buyAmount.value) * price) || (sellTokenId.value === constants.LINERA_NATIVE_ID ? 0.01 : 25)).toFixed(6)
    if (btnStep.value === 0 && Number(buyAmount.value) > 0 && Number(sellAmount.value) > 0) {
      btnStep.value += 1
    }
  }, 1000)
})

watch(fullPrecisionSellPrice, () => {
  if (Number(buyAmount.value) === 0) {
    buyAmount.value = ((Number(sellAmount.value) * fullPrecisionSellPrice.value) || 0).toFixed(6)
  }
})

interface BtnActionItem {
  label: string
  disable: boolean
}

enum BtnAction {
  InputAmount = 'Input amount',
  Review = 'Review',
  Swap = 'Swap'
}

const btnActions = ref([{
  label: BtnAction.InputAmount,
  disable: true
}, {
  label: BtnAction.Review,
  disable: false
}, {
  label: BtnAction.Swap,
  disable: false
}] as BtnActionItem[])
const btnStep = ref(0)

const onSwitchTokenClick = () => {
  const token = buyToken.value
  buyToken.value = sellToken.value
  sellToken.value = token

  const amount = sellAmount.value
  sellAmount.value = buyAmount.value
  buyAmount.value = amount
}

const onSwapClick = () => {
  reviewing.value = true
}

const onSwapDone = () => {
  buyAmount.value = '0'
  sellAmount.value = '0'
  reviewing.value = false
  btnStep.value = 0
}

const onSwapError = (e: string) => {
  reviewing.value = false
  notify.Notify.pushNotification({
    Title: 'Swap meme token',
    Message: `Failed swap meme token: ${e}`,
    Popup: true,
    Type: notify.NotifyType.Error
  })
}

const onSwapCanceled = () => {
  reviewing.value = false
}

const onSetSlippageClick = () => {
  settingSlippage.value = true
}

const onSetSlippageDone = (_slippage: number) => {
  settingSlippage.value = false
  console.log(_slippage, 111)
  slippage.value = _slippage
}

const onSetSlippageCanceled = () => {
  settingSlippage.value = false
}

const onShowTradeInfoClick = () => {
  showingTradeInfo.value = !showingTradeInfo.value
}

const gasTicker = ref(-1)
const swapGasAmount = ref('0')
const buyAmountMin = computed(() => (Number(buyAmount.value) * (1 - slippage.value)).toFixed(6))

onMounted(async () => {
  buyToken.value = tokens.value[0] as Token
  sellToken.value = undefined as unknown as Token

  await Wallet.estimateSwapGas(sellToken.value, buyToken.value, sellAmount.value, buyAmountMin.value, (gasAmount: string) => {
    swapGasAmount.value = gasAmount
  })
  gasTicker.value = window.setInterval(async () => {
    await Wallet.estimateSwapGas(sellToken.value, buyToken.value, sellAmount.value, buyAmountMin.value, (gasAmount: string) => {
      swapGasAmount.value = gasAmount
    })
  }, 30000)
})

onBeforeUnmount(() => {
  if (gasTicker.value >= 0) {
    window.clearInterval(gasTicker.value)
  }
})

</script>

<style scoped lang='sass'>
@media (max-width: 960px)
  .trade-action
    width: 100%

  .selected-token-info
    width: 100%
    margin-left: 0
    margin-top: 16px
</style>