<template>
  <div class='bg-white vertical-card-padding'>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ $t("MSG_LIQUIDITY") }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(ownerLiquidity).toFixed(4) }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          class='swap-amount-input text-grey-8' dense v-model.number='liquidityAmount' reverse-fill-mask
          input-class='text-right'
          :error='liquidityAmountError'
        />
      </div>
    </q-card>
    <q-expansion-item
      dense
      expand-icon-toggle
      expand-separator
      :label='$t("MSG_MORE_OPTIONS")'
      v-model='expanded'
      class='decorate-border-bottom vertical-inner-y-margin text-grey-8'
    >
      <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
        <div class='row'>
          <div>
            <div class='text-bold'>
              BBBBBBBBBBBBBBBBB
            </div>
            <div class='text-grey-8' title='bbbbbbbbbbbbbbbbb'>
              bbbbbbbbbbbbbbbbbbbb
            </div>
          </div>
          <q-space />
          <div class='row'>
            <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
            <div class='swap-amount-label text-grey-9 text-bold'>
              {{ Number(outBalance).toFixed(2) }}
            </div>
            <div class='text-grey-8'>
              BBBBBBBBBBBBBBBBBBB
            </div>
          </div>
        </div>
        <div class='row vertical-card-align swap-token'>
          <q-input
            class='swap-amount-input text-grey-8' dense v-model.number='tokenZeroAmount' reverse-fill-mask
            input-class='text-right'
            label='MinAmount'
            :error='tokenZeroAmountError'
          />
        </div>
      </q-card>
      <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
        <div class='row'>
          <div>
            <div class='text-bold'>
              BBBBBBBBBBBBBBB
            </div>
            <div class='text-grey-8' title='aaaaaaaaaaaaaaaaaa'>
              aaaaaaaaaaaaa
            </div>
          </div>
          <q-space />
          <div class='row'>
            <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
            <div class='swap-amount-label text-grey-9 text-bold'>
              {{ Number(inBalance).toFixed(2) }}
            </div>
            <div class='text-grey-8'>
              AAAAAAAAAAAA
            </div>
          </div>
        </div>
        <div class='row vertical-card-align swap-token'>
          <q-input
            class='swap-amount-input' dense v-model.number='tokenOneAmount' reverse-fill-mask
            input-class='text-right'
            label='MinAmount'
            :error='tokenOneAmountError'
          />
        </div>
      </q-card>
    </q-expansion-item>
    <q-btn
      rounded flat :label='$t("MSG_REMOVE_LIQUIDITY")' class='full-width border-red-4 vertical-inner-y-margin vertical-inner-y-margin-bottom'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const liquidityAmount = ref(1)
const tokenZeroAmount = ref(0)
const tokenOneAmount = ref(0)
const ownerLiquidity = ref(0)

const liquidityAmountError = ref(false)
const tokenZeroAmountError = ref(false)
const tokenOneAmountError = ref(false)

const outBalance = ref(0)
const inBalance = ref(0)

const expanded = ref(false)

const subscriptionId = ref(undefined as unknown as string)

watch(liquidityAmount, (amount) => {
  if (liquidityAmount.value > ownerLiquidity.value) {
    liquidityAmountError.value = true
    return
  }
  liquidityAmountError.value = false
  if (amount === null || amount < 0) {
    liquidityAmount.value = 1
  }
})

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
  margin-top: -6px

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
