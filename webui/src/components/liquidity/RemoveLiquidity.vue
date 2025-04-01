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
            {{ Number(liquidity?.liquidity).toFixed(4) }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          dense filled reverse-fill-mask hide-bottom-space
          class='swap-amount-input text-grey-8' v-model.number='liquidityAmount'
          input-class='text-left text-bold text-green-8'
          :input-style='{fontSize: "20px"}'
          :error='liquidityAmountError'
        >
          <template #append>
            <q-btn
              dense
              flat
              :label='$t("MSG_MAX")'
              @click='onMaxClick'
              class='text-blue-6'
            />
          </template>
        </q-input>
      </div>
    </q-card>
    <div class='vertical-item-y-margin text-grey-8 text-left text-bold'>
      {{ $t("MSG_ESTIMATED_WITHDRAW") }}
    </div>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ token0 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(token0, 12) }}
          </div>
        </div>
        <q-space />
        <div class='swap-token text-right'>
          <div class='swap-amount-input text-green-8 text-bold'>{{ Number(liquidity?.amount0).toFixed(4) }}</div>
        </div>
      </div>
    </q-card>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
      <div class='row'>
        <div>
          <div class='text-bold'>
            {{ token1Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ token1 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(token1, 12) }}
          </div>
        </div>
        <q-space />
        <div class='swap-token text-right'>
          <div class='swap-amount-input text-green-8 text-bold'>{{ Number(liquidity?.amount1).toFixed(4) }}</div>
        </div>
      </div>
    </q-card>
    <q-btn
      rounded flat :label='$t("MSG_REMOVE_LIQUIDITY")' class='full-width border-red-4 vertical-inner-y-margin'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, watch, onMounted, computed } from 'vue'
import { swap, ams, meme, pool, user, account } from 'src/localstore'
import { constants } from 'src/constant'
import { shortid } from 'src/utils'

const _swap = swap.useSwapStore()
const _ams = ams.useAmsStore()
const _user = user.useUserStore()

const token0 = computed(() => _swap.selectedToken0)
const token1 = computed(() => _swap.selectedToken1)
const selectedPool = computed(() => _swap.selectedPool)
const poolApplication = computed(() => selectedPool.value?.poolApplication as account.Account)

const token0Ticker = computed(() => token0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(token0.value)?.spec || '{}') as meme.Meme).ticker)
const token1Ticker = computed(() => token1.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(token1.value)?.spec || '{}') as meme.Meme).ticker)

const liquidity = ref({} as pool.LiquidityAmount)

const liquidityAmount = ref(0)
const liquidityAmountError = ref(false)

watch(liquidityAmount, (amount) => {
  if (liquidityAmount.value > Number(liquidity.value?.liquidity)) {
    liquidityAmountError.value = true
    return
  }
  liquidityAmountError.value = false
  if (amount === null || amount < 0) {
    liquidityAmount.value = 1
  }
})

const onMaxClick = () => {
  liquidityAmount.value = Number(liquidity.value?.liquidity)
}

onMounted(async () => {
  pool.liquidity(await _user.account(), poolApplication.value, (_liquidity?: pool.LiquidityAmount) => {
    liquidity.value = _liquidity as pool.LiquidityAmount
  })
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
  margin: 8px 0 0 0
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

:deep(.q-item, .q-item--dense)
  padding: 0 !important
</style>
