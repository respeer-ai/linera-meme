<template>
  <q-page class='flex items-center justify-center'>
    <q-card flat class='create-pool-card'>
      <h5 class='text-center text-bold text-grey-8'>
        Create pool
      </h5>
      <q-separator />
      <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
        <div class='row'>
          <div>
            <div class='text-bold'>
              {{ token0Ticker }}
            </div>
            <div class='text-grey-8'>
              {{ shortId(token0 || '', 12, 8) }}
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
            :input-style='{fontSize: "28px"}'
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
          <div>
            <div class='text-bold'>
              {{ token1Ticker }}
            </div>
            <div class='text-grey-8'>
              {{ token1 === constants.LINERA_NATIVE_ID ? '' : shortId(token1 || '', 12, 8) }}
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
            :input-style='{fontSize: "28px"}'
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
      <q-btn
        rounded
        flat
        :label='$t("MSG_CREATE_POOL")'
        class='full-width border-red-4 vertical-section-y-margin vertical-inner-y-margin-bottom'
        @click='onCreatePoolClick'
      />
    </q-card>
  </q-page>
</template>

<script setup lang='ts'>
import { shortId } from 'src/utils/shortid'
import { ref, watch, onMounted, toRef, computed } from 'vue'
import { ams, meme, user, proxy, account } from 'src/localstore'
import { constants } from 'src/constant'

interface Props {
  token0: string
  token1: string
}

// eslint-disable-next-line no-undef
const props = defineProps<Props>()
const token0 = toRef(props, 'token0')
const token1 = toRef(props, 'token1')

const _ams = ams.useAmsStore()
const _user = user.useUserStore()
const _proxy = proxy.useProxyStore()

const token0Application = computed(() => _proxy.application(token0.value) as account.Account)
const token1Application = computed(() => _proxy.application(token1.value) as account.Account)
const token0Ticker = computed(() => token0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(token0.value)?.spec || '{}') as meme.Meme).ticker)
const token1Ticker = computed(() => token1.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(token1.value)?.spec || '{}') as meme.Meme).ticker)

const token0Amount = ref(0)
const token1Amount = ref(0)

const token0AmountError = ref(false)
const token1AmountError = ref(false)

const token0Balance = ref(0)
const token1Balance = ref(0)

const userBalance = computed(() => Number(_user.chainBalance) + Number(_user.accountBalance))

watch(token0Amount, () => {
  token0Amount.value = token0Amount.value < 0 ? 0 : token0Amount.value
})

watch(token1Amount, () => {
  token1Amount.value = token1Amount.value < 0 ? 0 : token1Amount.value
})

const refreshBalances = async () => {
  if (token0.value === constants.LINERA_NATIVE_ID) {
    token0Balance.value = userBalance.value
  } else {
    await meme.balanceOfMeme(token0Application.value, (balance: string) => {
      token0Balance.value = Number(Number(balance).toFixed(4))
    })
  }

  if (token1.value === constants.LINERA_NATIVE_ID) {
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

const onCreatePoolClick = () => {
  token0AmountError.value = token0Amount.value <= 0 || token0Amount.value > token0Balance.value
  token1AmountError.value = token1Amount.value <= 0 || token1Amount.value > token1Balance.value
  // TODO: create pool by miner
}

const onToken0AmountFocus = () => {
  token0AmountError.value = false
}

const onToken1AmountFocus = () => {
  token1AmountError.value = false
}

onMounted(async () => {
  getApplications()
  await refreshBalances()
})

</script>

<style scoped lang='sass'>
.create-pool-card
  border: 1px solid $red-4
  border-radius: 16px
  padding: 0 16px 16px 16px
  width: 440px

.swap-amount-label
  font-size: 28px
  margin-left: 4px
  margin-right: 4px
  margin-top: -14px

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

.exchange-separator
  width: calc(50% - 14px)
  margin-bottom: 12px
</style>
