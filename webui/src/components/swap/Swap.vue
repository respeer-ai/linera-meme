<template>
  <div class='bg-white'>
    <q-separator />
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-inner-y-margin'>
      <div class='row'>
        <div class='text-bold text-grey-8'>
          {{ $t('MSG_YOU_ARE_SELLING') }}
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill' class='text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ token0Balance }}
          </div>
          <div class='text-grey-8'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8' title='aaaaaaaaaaa'>
            {{ shortid.shortId(selectedToken0, 12) }}
          </div>
        </div>
        <q-space />
        <q-input
          class='swap-amount-input text-grey-8' dense v-model.number='outAmount' reverse-fill-mask
          input-class='text-right'
          :error='outAmountError'
        />
      </div>
    </q-card>
    <div class='row vertical-card-align'>
      <div class='decorate-border-bottom-bold exchange-separator' />
      <div class='exchange-symbol' size='28px'>
        <q-icon name='bi-arrow-down-up' size='14px' class='text-grey-6 cursor-pointer' @click='onExchangeClick' />
      </div>
      <div class='decorate-border-bottom-bold exchange-separator' />
    </div>
    <q-card flat class='bg-red-1 border-radius-8px popup-padding vertical-card-align'>
      <div class='row'>
        <div class='text-bold text-grey-8'>
          {{ $t('MSG_YOU_ARE_BUYING') }}
        </div>
        <q-space />
        <div class='row'>
          <q-icon name='bi-wallet-fill' class='text-grey-8 swap-amount-icon' size='16px' />
          <div class='swap-amount-label text-grey-9 text-bold'>
            {{ token1Balance }}
          </div>
          <div class='text-grey-8'>
            {{ token1Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <div>
          <div class='text-bold'>
            {{ token1Ticker }}
          </div>
          <div class='text-grey-8' title='aaaaaaaaaaa'>
            {{ shortid.shortId(selectedToken1, 12) }}
          </div>
        </div>
        <q-space />
        <q-input
          class='swap-amount-input' dense v-model.number='inAmount' reverse-fill-mask
          input-class='text-right'
        />
      </div>
    </q-card>
    <q-btn
      rounded flat :label='$t("MSG_SWAP")' class='full-width border-red-4 vertical-inner-y-margin vertical-inner-y-margin-bottom'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, computed, watch, onMounted } from 'vue'
import { swap, ams, meme, user, block, account, notify, proxy } from 'src/localstore'
import { constants } from 'src/constant'
import { shortid } from 'src/utils'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'

const _swap = swap.useSwapStore()
const _ams = ams.useAmsStore()
const _user = user.useUserStore()
const _block = block.useBlockStore()
const _meme = meme.useMemeStore()
const _proxy = proxy.useProxyStore()

const selectedPool = computed(() => _swap.selectedPool)

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const token0Ticker = computed(() => selectedToken0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(selectedToken0.value)?.spec || '{}') as meme.Meme).ticker)
const token1Ticker = computed(() => selectedToken1.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(selectedToken1.value)?.spec || '{}') as meme.Meme).ticker)
const token0Chain = computed(() => _proxy.chain(selectedToken0.value) as Chain)
const token1Chain = computed(() => _proxy.chain(selectedToken1.value) as Chain)
const token0Application = computed(() => {
  return {
    chainId: token0Chain.value?.chainId,
    owner: `Application:${token0Chain.value?.token}`
  }
})
const token1Application = computed(() => {
  return {
    chainId: token1Chain.value?.chainId,
    owner: `Application:${token1Chain.value?.token}`
  }
})
const userChainBalance = computed(() => _user.chainBalance)
const userOwnerBalance = computed(() => _user.accountBalance)
const userBalance = computed(() => Number((Number(userChainBalance.value) + Number(userOwnerBalance.value)).toFixed(4)))

const token0Balance = ref(0)
const token1Balance = ref(0)

const outAmount = ref(0)
const inAmount = ref(0)

const outAmountError = ref(false)

const blockHeight = computed(() => _block.blockHeight)

const balanceOfMeme = async (tokenApplication: account.Account, done: (balance: string) => void) => {
  const owner = await _user.account()
  if (!owner.owner || !token0Chain.value || !tokenApplication.owner) return
  const owenrDescription = account._Account.accountDescription(owner)

  _meme.balanceOf({
    owner: owenrDescription,
    Message: {
      Error: {
        Title: 'Balance of meme',
        Message: 'Failed get balance of meme',
        Popup: true,
        Type: notify.NotifyType.Error
      }
    }
  }, tokenApplication, (error: boolean, balance?: string) => {
    if (error) return
    done(balance as string)
  })
}

const refreshBalances = async () => {
  if (selectedToken0.value === constants.LINERA_NATIVE_ID) {
    token0Balance.value = userBalance.value
  } else {
    await balanceOfMeme(token0Application.value, (balance: string) => {
      token0Balance.value = Number(Number(balance).toFixed(4))
    })
  }

  if (selectedToken1.value === constants.LINERA_NATIVE_ID) {
    token1Balance.value = userBalance.value
  } else {
    await balanceOfMeme(token1Application.value, (balance: string) => {
      token1Balance.value = Number(Number(balance).toFixed(4))
    })
  }
}

watch(userBalance, () => {
  if (selectedToken0.value === constants.LINERA_NATIVE_ID) {
    token0Balance.value = userBalance.value
  }

  if (selectedToken1.value === constants.LINERA_NATIVE_ID) {
    token1Balance.value = userBalance.value
  }
})

watch(blockHeight, async () => {
  await refreshBalances()
})

watch(token0Chain, async () => {
  await refreshBalances()
})

watch(token1Chain, async () => {
  await refreshBalances()
})

const onExchangeClick = () => {
  _swap.selectedToken0 = selectedToken1.value
  _swap.selectedToken1 = selectedToken0.value
}

onMounted(async () => {
  await refreshBalances()
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
  width: calc(100% - 160px)

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
