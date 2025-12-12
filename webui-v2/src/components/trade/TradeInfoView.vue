<template>
  <div class='q-px-lg'>
    <div class='text-neutral font-size-24'>You're swapping</div>
    <div class='row q-mt-lg items-center'>
      <div>
        <div class='font-size-28 text-light'>{{ sellAmount }} {{ sellTokenTicker }}</div>
        <div class='font-size-24 text-neutral'>$ 0.00</div>
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
        <div class='font-size-28 text-light'>{{ buyAmount }} {{ buyTokenTicker }}</div>
        <div class='font-size-24 text-neutral'>$ 0.00</div>
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
      <token-info-line-view label='Fee (0.25%)' value='0.00001245 TLINERA ($ 0.007)' value-color='light' :value-bold='false' :underline='false' />
      <div class='q-mt-sm'>
        <token-info-line-view label='Network Fee' value='0.0001234 TLINERA ($ 0.0008)' value-color='light' :value-bold='false' :underline='false' />
      </div>
      <div v-if='expanded' class='q-mt-sm'>
        <token-info-line-view label='Price' :value='`1 ${sellTokenTicker} = ${sellPrice} ${buyTokenTicker}`' value-color='light' :value-bold='false' :underline='false' />
      </div>
      <div v-if='expanded'  class='q-mt-sm'>
        <token-info-line-view label='Slippage' value='0.55% (Automatically)' value-color='neutral' :value-bold='false' :underline='false' />
      </div>
      <div v-if='expanded'  class='q-mt-sm'>
        <token-info-line-view label='Order Router' value='MicroMeme Proxy' value-color='light' :value-bold='false' :underline='false' />
      </div>
      <div v-if='expanded' class='q-mt-sm'>
        <token-info-line-view label='Price Impact' value='-0.05%' value-color='neutral' :value-bold='false' :underline='false' />
      </div>
    </div>

    <div class='q-mt-lg'>
      <q-btn no-caps rounded class='fill-parent-width bg-primary q-mt-sm font-size-20' @click='onSwapClick' :loading='swapping'>
        Swap
      </q-btn>
      <q-btn no-caps rounded class='fill-parent-width border-primary-50 q-mt-sm font-size-20' @click='onCancelClick'>
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

import TokenInfoLineView from './TokenInfoLineView.vue'
import { Wallet } from 'src/wallet'

interface Props {
  sellToken: Token
  sellAmount: string
  buyToken: Token
  buyAmount: string
  sellPrice: string
}
const props = defineProps<Props>()
const sellToken = toRef(props, 'sellToken')
const buyToken = toRef(props, 'buyToken')
const sellAmount = toRef(props, 'sellAmount')
const buyAmount = toRef(props, 'buyAmount')
const sellPrice = toRef(props, 'buyAmount')

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

  await Wallet.swap(sellToken.value, buyToken.value, sellAmount.value, () => {
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
