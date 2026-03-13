<template>
  <div class='q-px-lg'>
    <div class='text-neutral font-size-20'>You're swapping</div>
    <q-separator class='q-mt-sm' color='nautral' />
    <div class='row q-mt-lg items-center'>
      <div>
        <div class='font-size-24 text-light'>{{ sellAmount }} {{ sellTokenTicker }}</div>
        <div class='font-size-20 text-neutral'>$ 0.00</div>
      </div>
      <q-space />
      <div>
        <q-avatar size='80px'>
          <q-img :src='sellTokenLogo' width='64px' height='64px' />
        </q-avatar>
      </div>
    </div>

    <div class='q-mt-lg'>
      <q-icon name='arrow_downward' size='28px' class='text-grey-8' />
    </div>

    <div class='row q-mt-lg items-center'>
      <div>
        <div class='font-size-24 text-light'>{{ buyAmount }} {{ buyTokenTicker }}</div>
        <div class='font-size-20 text-neutral'>$ 0.00</div>
      </div>
      <q-space />
      <div>
        <q-avatar size='80px'>
          <q-img :src='buyTokenLogo' width='64px' height='64px' />
        </q-avatar>
      </div>
    </div>

    <div class='line-with-text font-size-18 q-mt-lg row items-center'>
      <div class='row cursor-pointer' @click='onExpandClick'>
        <div>Expand</div>
        <q-icon :name='expanded ? "keyboard_double_arrow_up" : "keyboard_double_arrow_down"' size='24px' />
      </div>
    </div>

    <div class='q-mt-lg'>
      <trade-detail-view
        :buy-token='buyToken'
        :sell-token='sellToken'
        :buy-amount='buyAmount'
        :sell-amount='sellAmount'
        :sell-price='sellPrice'
        :slippage='slippage'
        :price-impact='priceImpact'
        :expanded='expanded'
      />
    </div>

    <div class='q-mt-lg'>
      <q-btn no-caps rounded class='fill-parent-width bg-primary q-mt-sm font-size-20' @click='onSwapClick' :loading='swapping'>
        Swap
      </q-btn>
      <q-btn no-caps rounded class='fill-parent-width border-primary-50 q-mt-sm font-size-20' @click='onCancelClick' :disabled='swapping'>
        Cancel
      </q-btn>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { computed, ref, toRef } from 'vue'
import { Token } from './Token'
import { constants } from 'src/constant'
import { ams } from 'src/stores/export'
import { Wallet } from 'src/wallet'

import TradeDetailView from './TradeDetailView.vue'

interface Props {
  sellToken: Token
  sellAmount: string
  buyToken: Token
  buyAmount: string
  sellPrice: string
  slippage: number
  priceImpact: string
}
const props = defineProps<Props>()
const sellToken = toRef(props, 'sellToken')
const buyToken = toRef(props, 'buyToken')
const sellAmount = toRef(props, 'sellAmount')
const buyAmount = toRef(props, 'buyAmount')
const sellPrice = toRef(props, 'buyAmount')
const slippage = toRef(props, 'slippage')
const priceImpact = toRef(props, 'priceImpact')
const buyAmountMin = computed(() => (Number(buyAmount.value) * (1 - slippage.value)).toFixed(6))

const sellTokenTicker = computed(() => sellToken.value?.meme?.ticker || constants.LINERA_TICKER)
const buyTokenTicker = computed(() => buyToken.value?.meme?.ticker || constants.LINERA_TICKER)
const sellTokenLogo = computed(() => ams.Ams.applicationLogo(sellToken.value) || constants.LINERA_LOGO)
const buyTokenLogo = computed(() => ams.Ams.applicationLogo(buyToken.value) || constants.LINERA_LOGO)

const expanded = ref(false)
const swapping = ref(false)

const emit = defineEmits<{
  (e: 'done'): void,
  (e: 'error', error: string): void,
  (e: 'cancel'): void
}>()

const onExpandClick = () => {
  expanded.value = !expanded.value
}

const onSwapClick = async () => {
  swapping.value = true

  await Wallet.swap(sellToken.value, buyToken.value, sellAmount.value, buyAmountMin.value, () => {
    emit('done')
    swapping.value = false
  }, (e) => {
    emit('error', e)
    swapping.value = false
  })
}

const onCancelClick = () => {
  emit('cancel')
}

</script>
