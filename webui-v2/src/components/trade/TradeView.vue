<template>
  <div class='row content-start wrap'>
    <div class='trade-action'>
      <div class='row items-center'>
        <token-input-view :action='TokenAction.Sell' style='width: calc(50% - 4px);' v-model='sellToken' />
        <div class='radius-24 bg-accent q-pa-sm cursor-pointer hover-primary' style='height: 48px; width: 48px; margin-left: -20px; z-index: 1000;'>
          <q-icon name='arrow_forward' size='32px' />
        </div>
        <token-input-view :action='TokenAction.Buy' style='width: calc(50% - 4px); margin-left: -20px;' :auto-focus='false' v-model='buyToken' />
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
import { ref } from 'vue'

import TokenInputView from './TokenInputView.vue'
import TokenInfoView from './TokenInfoView.vue'
import PriceChartView from '../kline/PriceChartView.vue'

const buyToken = ref(undefined as unknown as Token)
const sellToken = ref(undefined as unknown as Token)

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