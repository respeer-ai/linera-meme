<template>
  <q-card flat :class='[ "create-pool-card", inPage ? "in-page" : "" ]'>
    <h5 class='text-center text-bold text-grey-8' v-if='title'>
      {{ $t(title) }}
    </h5>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div>
          <div class='row'>
            <q-img :src='token0Logo' width='24px' height='24px' fit='contain' />
            <div class='text-bold'>
              {{ token0Ticker }}
            </div>
          </div>
          <div class='text-grey-8'>
            {{ shortId(token0 || '', 8, 6) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(token0Balance).toFixed(4) }}
          </div>
          <div class='text-grey-8'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          dense
          filled
          reverse-fill-mask
          hide-bottom-space
          class='swap-amount-input text-grey-8'
          v-model.number='token0Amount'
          input-class='text-left text-bold text-green-8'
          :input-style='{fontSize: inPage ? "28px" : "20px"}'
          :error='token0AmountError'
          @focus='onToken0AmountFocus'
        >
          <template #append>
            <q-btn
              dense
              flat
              :label='$t("MSG_MAX")'
              @click='onToken0MaxClick'
              class='text-blue-6'
            />
          </template>
        </q-input>
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
        <div v-if='selectable'>
          <q-select
            dense filled hide-dropdown-icon
            v-model='selectedToken1' :options='token1Items'
            class='swap-token-option'
          >
            <template #option='scope'>
              <q-item dense v-bind='scope.itemProps'>
                <q-img :src='scope.opt.logo' width='24px' height='24px' fit='contain' />
                <div class='horizontal-inner-x-margin-left'>
                  <div class='row'>
                    <div class='swap-token-name text-bold'>
                      {{ scope.opt.ticker }}
                    </div>
                    <q-space />
                  </div>
                  <div>{{ scope.opt.name }}</div>
                </div>
              </q-item>
            </template>
            <template #selected>
              <div class='row'>
                <q-img :src='selectedToken1?.logo' width='24px' height='24px' fit='contain' />
                <div class='swap-token-name text-bold swap-token-label flex items-center justify-center' :style='{marginLeft: "8px"}'>
                  {{ selectedToken1?.ticker }}
                </div>
              </div>
            </template>
          </q-select>
        </div>
        <div v-else>
          <div class='text-bold'>
            {{ token1Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ _token1 === constants.LINERA_NATIVE_ID ? '' : shortId(_token1 || '', 8, 8) }}
          </div>
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ Number(token1Balance).toFixed(4) }}
          </div>
          <div class='text-grey-8'>
            {{ token1Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <q-input
          dense
          filled
          reverse-fill-mask
          hide-bottom-space
          class='swap-amount-input text-grey-8'
          v-model.number='token1Amount'
          input-class='text-left text-bold text-green-8'
          :input-style='{fontSize: inPage ? "28px" : "20px"}'
          :error='token1AmountError'
          @focus='onToken1AmountFocus'
        >
          <template #append>
            <q-btn
              dense
              flat
              :label='$t("MSG_MAX")'
              @click='onToken1MaxClick'
              class='text-blue-6'
            />
          </template>
        </q-input>
      </div>
    </q-card>
    <div v-if='!selectable'>
      <div class='vertical-item-y-margin text-grey-8 text-left text-bold'>
        {{ $t("MSG_ESTIMATED_SHARE") }}
      </div>
      <q-card flat class='bg-red-1 border-radius-8px popup-padding'>
        <div class='row'>
          <div class='text-bold'>
            {{ $t('MSG_LIQUIDITY') }}
          </div>
          <q-space />
          <div class='swap-token text-right'>
            <div class='text-green-8 text-bold'>{{ Number(estimatedLiquidity?.liquidity || '0').toFixed(10) }}</div>
          </div>
        </div>
      </q-card>
      <div class='vertical-item-y-margin text-grey-8 text-left text-bold'>
        {{ $t("MSG_ESTIMATED_DEPOSIT") }}
      </div>
      <q-card flat class='bg-red-1 border-radius-8px popup-padding'>
        <div class='row'>
          <div>
            <div class='text-bold'>
              {{ token0Ticker }}
            </div>
            <div class='text-grey-8' v-if='token0 !== constants.LINERA_NATIVE_ID'>
              {{ token0 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(token0, 12) }}
            </div>
          </div>
          <q-space />
          <div class='swap-token text-right'>
            <div class='text-green-8 text-bold'>{{ Number(estimatedLiquidity?.amount0 || '0').toFixed(10) }}</div>
          </div>
        </div>
      </q-card>
      <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
        <div class='row'>
          <div>
            <div class='text-bold'>
              {{ token1Ticker }}
            </div>
            <div class='text-grey-8' v-if='_token1 !== constants.LINERA_NATIVE_ID'>
              {{ _token1 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(_token1, 12) }}
            </div>
          </div>
          <q-space />
          <div class='swap-token text-right'>
            <div class='text-green-8 text-bold'>{{ Number(estimatedLiquidity?.amount1 || '0').toFixed(10) }}</div>
          </div>
        </div>
      </q-card>
    </div>
    <q-btn
      rounded
      flat
      :label='$t(nextLabel)'
      :class='[ "full-width border-red-4", inPage ? "vertical-inner-y-margin-bottom vertical-section-y-margin" : "vertical-inner-y-margin" ]'
      @click='onNextClick'
      :disable='token0Amount === 0 || token1Amount === 0'
    />
  </q-card>
</template>

<script setup lang='ts'>
import { shortId } from 'src/utils/shortid'
import { ref, watch, onMounted, toRef, computed } from 'vue'
import { ams, meme, user, proxy, account, pool, swap } from 'src/localstore'
import { constants } from 'src/constant'
import { shortid } from 'src/utils'

interface Props {
  title?: string
  nextLabel: string
  token0: string
  token1: string
  inPage?: boolean
  selectable?: boolean
  token1Items?: meme.TokenItem[]
}

// TODO: calculate token pair amount

// eslint-disable-next-line no-undef
const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  inPage: true,
  selectable: false
})
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')
const token1Items = toRef(props, 'token1Items')
const selectable = toRef(props, 'selectable')

const _token1 = ref(token1.value)

const _ams = ams.useAmsStore()
const _user = user.useUserStore()
const _proxy = proxy.useProxyStore()
const _swap = swap.useSwapStore()

const selectedPool = computed(() => _swap.selectedPool)
const selectedToken1 = ref(token1Items.value?.find((el) => el.token === constants.LINERA_NATIVE_ID) as meme.TokenItem || token1Items.value?.[0] as meme.TokenItem)

const token0Application = computed(() => _proxy.application(token0.value) as account.Account)
const token1Application = computed(() => _proxy.application(_token1.value) as account.Account)
const token0Ticker = computed(() => token0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(token0.value)?.spec || '{}') as meme.Meme).ticker)
const token0Logo = computed(() => token0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_LOGO : _ams.applicationLogo(_ams.application(token0.value) as ams.Application))
const token1Ticker = computed(() => _token1.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(_token1.value)?.spec || '{}') as meme.Meme).ticker)

const token0Amount = ref(0)
const token1Amount = ref(0)

const estimatedLiquidity = ref({} as pool.LiquidityAmount)

const token0AmountError = ref(false)
const token1AmountError = ref(false)

const token0Balance = ref(0)
const token1Balance = ref(0)

const userBalance = computed(() => Number(_user.chainBalance) + Number(_user.accountBalance))

const calculateLiquidityAmount = () => {
  if (token0Amount.value <= 0 || token1Amount.value <= 0) {
    return
  }
  if (!selectedPool.value) return
  pool.calculateAmountLiquidity(token0Amount.value.toString(), token1Amount.value.toString(), selectedPool.value.poolApplication, (_liquidity?: pool.LiquidityAmount) => {
    estimatedLiquidity.value = _liquidity as pool.LiquidityAmount
  })
}

watch(selectedPool, () => {
  calculateLiquidityAmount()
})

watch(token0Amount, () => {
  token0Amount.value = token0Amount.value < 0 ? 0 : token0Amount.value
  calculateLiquidityAmount()
})

watch(token1Amount, () => {
  token1Amount.value = token1Amount.value < 0 ? 0 : token1Amount.value
  calculateLiquidityAmount()
})

const refreshBalances = async () => {
  if (token0.value === constants.LINERA_NATIVE_ID) {
    token0Balance.value = userBalance.value
  } else {
    await meme.balanceOfMeme(token0Application.value, (balance: string) => {
      token0Balance.value = Number(Number(balance).toFixed(4))
    })
  }

  if (_token1.value === constants.LINERA_NATIVE_ID) {
    token1Balance.value = userBalance.value
  } else {
    await meme.balanceOfMeme(token1Application.value, (balance: string) => {
      token1Balance.value = Number(Number(balance).toFixed(4))
    })
  }
}

watch(token0Application, async () => {
  await refreshBalances()
})

watch(token1Application, async () => {
  await refreshBalances()
})

watch(userBalance, async () => {
  await refreshBalances()
})

const getApplications = () => {
  ams.getApplications((error: boolean, rows?: ams.Application[]) => {
    // eslint-disable-next-line no-useless-return
    if (error || !rows?.length) return
    // Continue to fetch
  })
}

const onToken1MaxClick = () => {
  token1Amount.value = token1Balance.value
}

const onToken0MaxClick = () => {
  token0Amount.value = token0Balance.value
}

// eslint-disable-next-line no-undef
const emit = defineEmits<{(ev: 'next', token0Amount: number, token1Amount: number, token1?: string): void}>()

const onNextClick = () => {
  token0AmountError.value = token0Amount.value <= 0 || token0Amount.value > token0Balance.value
  token1AmountError.value = token1Amount.value <= 0 || token1Amount.value > token1Balance.value
  if (token0AmountError.value || token1AmountError.value) return

  emit('next', token0Amount.value, token1Amount.value, _token1.value)
}

const onToken0AmountFocus = () => {
  token0AmountError.value = false
}

const onToken1AmountFocus = () => {
  token1AmountError.value = false
}

watch(token1Items, () => {
  selectedToken1.value = selectedToken1.value || token1Items.value?.find((el) => el.token === constants.LINERA_NATIVE_ID) as meme.TokenItem || token1Items.value?.[0] as meme.TokenItem
})

watch(selectedToken1, () => {
  if (!selectable.value) return
  _token1.value = selectedToken1.value.token || _token1.value
})

onMounted(async () => {
  if (selectable.value && !_token1.value) {
    _token1.value = selectedToken1.value?.token || _token1.value
  }
  getApplications()
  await refreshBalances()
  calculateLiquidityAmount()
})

</script>

<style scoped lang='sass'>
.create-pool-card
  border-radius: 16px

.in-page
  border: 1px solid $red-4
  padding: 0 16px 16px 16px
  width: 440px
  .swap-amount-label
    font-size: 28px
    margin-top: -14px

.swap-amount-label
  font-size: 20px
  margin-left: 4px
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
  margin-top: 8px

.exchange-symbol
  border: 2px solid $grey-4
  border-radius: 50%
  width: 28px
  height: 28px
  padding: 2px 5px

.swap-token-option
  display: inline-block
  border-radius: 4px

.swap-token-name
  line-height: 26px

.exchange-separator
  width: calc(50% - 14px)
  margin-bottom: 12px
</style>
