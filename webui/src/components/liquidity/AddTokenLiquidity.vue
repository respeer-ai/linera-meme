<template>
  <div class='bg-white popup-padding'>
    <h5>Add Liquidity</h5>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8' :title='token0Id'>
            {{ shortId(token0Id || '', 5) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(outBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input text-grey-8' dense v-model.number='tokenZeroAmount' reverse-fill-mask
          input-class='text-right'
          :error='tokenZeroAmountError'
        />
      </div>
    </q-card>
    <div class='row vertical-card-align'>
      <div class='decorate-border-bottom-bold exchange-separator' />
      <div class='exchange-symbol' size='28px'>
        <q-icon name='bi-three-dots' size='14px' class='text-grey-6' />
      </div>
      <div class='decorate-border-bottom-bold exchange-separator' />
    </div>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            WTLINERA
          </div>
          <div class='text-grey-8' title='AAAAAAAAAAAAAAAAAA'>
            aaaaaaaaaaaaaaaa
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(inBalance).toFixed(2) }}
          </div>
          <div class='text-grey-8'>
            WTLINERA
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input' dense v-model.number='tokenOneAmount' reverse-fill-mask
          input-class='text-right'
          :error='tokenOneAmountError'
        />
      </div>
    </q-card>
    <q-btn
      rounded flat :label='$t("MSG_ADD_LIQUIDITY")' class='full-width border-red-4 vertical-inner-y-margin vertical-inner-y-margin-bottom'
    />
  </div>
</template>

<script setup lang='ts'>
import { shortId } from 'src/utils/shortid'
import { ref, watch, onMounted, onUnmounted, toRef } from 'vue'

interface Props {
  token0Id: string
  token0Ticker: string
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const token0Id = toRef(props, 'token0Id')

const tokenZeroAmount = ref(0)
const tokenOneAmount = ref(0)

const tokenZeroAmountError = ref(false)
const tokenOneAmountError = ref(false)

const outBalance = ref(0)
const inBalance = ref(0)

const subscriptionId = ref(undefined as unknown as string)

watch(tokenZeroAmount, (amount) => {
  if (amount === null || amount < 0) {
    tokenZeroAmount.value = 0
  }
})

watch(tokenOneAmount, (amount) => {
  if (amount === null || amount < 0) {
    tokenOneAmount.value = 0
  }
})

const subscriptionHandler = () => {
  // TODO
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
.swap-amount-label
  font-size: 20px
  margin-right: 4px

.swap-amount-icon
  margin-right: 4px
  margin-top: 2px

:deep(.swap-token)
  .q-select
    .q-icon
      font-size: 16px

.swap-amount-input
  width: 100%

.exchange-symbol
  border: 2px solid $grey-4
  border-radius: 50%
  width: 28px
  height: 28px
  padding: 2px 5px

.exchange-separator
  width: calc(50% - 14px)
  margin-bottom: 12px
</style>
