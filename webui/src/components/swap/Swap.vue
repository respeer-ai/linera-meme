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
          <div class='text-grey-8' v-if='selectedToken0 !== constants.LINERA_NATIVE_ID'>
            {{ token0Ticker }}
          </div>
        </div>
      </div>
      <div class='row vertical-card-align swap-token'>
        <div>
          <div class='text-bold'>
            {{ token0Ticker }}
          </div>
          <div class='text-grey-8'>
            {{ selectedToken0 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(selectedToken0, 12) }}
          </div>
        </div>
        <q-space />
        <q-input
          dense filled reverse-fill-mask hide-bottom-space
          class='swap-amount-input text-grey-8' v-model.number='token0Amount'
          input-class='text-left text-bold text-green-8'
          :input-style='{fontSize: "20px"}'
          :error='token0AmountError'
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
          <div class='text-grey-8'>
            {{ selectedToken1 === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : shortid.shortId(selectedToken1, 12) }}
          </div>
        </div>
        <q-space />
        <q-input
          dense filled reverse-fill-mask hide-bottom-space
          class='swap-amount-input' v-model.number='token1Amount'
          input-class='text-left text-bold text-green-8'
          :input-style='{fontSize: "20px"}'
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
      rounded flat :label='$t("MSG_SWAP")' class='full-width border-red-4 vertical-inner-y-margin'
      @click='onSwapClick'
      :disable='token0Amount === 0 || token1Amount === 0'
    />
  </div>
</template>

<script setup lang='ts'>
import { ref, computed, watch, onMounted } from 'vue'
import { swap, ams, meme, user, block, account, proxy, pool } from 'src/localstore'
import { constants } from 'src/constant'
import { shortid } from 'src/utils'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { SWAP } from 'src/graphql'
import * as lineraWasm from '../../../dist/wasm/linera_wasm'
import { stringify } from 'lossless-json'

const _swap = swap.useSwapStore()
const _ams = ams.useAmsStore()
const _user = user.useUserStore()
const _block = block.useBlockStore()
const _proxy = proxy.useProxyStore()
const _pool = pool.usePoolStore()

const selectedPool = computed(() => _swap.selectedPool)

const selectedToken0 = computed(() => _swap.selectedToken0)
const selectedToken1 = computed(() => _swap.selectedToken1)
const token0Ticker = computed(() => selectedToken0.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(selectedToken0.value)?.spec || '{}') as meme.Meme).ticker)
const token1Ticker = computed(() => selectedToken1.value === constants.LINERA_NATIVE_ID ? constants.LINERA_TICKER : (JSON.parse(_ams.application(selectedToken1.value)?.spec || '{}') as meme.Meme).ticker)
const token0Chain = computed(() => _proxy.chain(selectedToken0.value) as Chain)
const token1Chain = computed(() => _proxy.chain(selectedToken1.value) as Chain)
const token0Application = computed(() => {
  return {
    chainId: token0Chain.value?.chainId as string,
    owner: token0Chain.value?.token as string
  }
})
const token1Application = computed(() => {
  return {
    chainId: token1Chain.value?.chainId as string,
    owner: token1Chain.value?.token as string
  }
})
const userChainBalance = computed(() => _user.chainBalance)
const userOwnerBalance = computed(() => _user.accountBalance)
const userBalance = computed(() => Number((Number(userChainBalance.value) + Number(userOwnerBalance.value)).toFixed(4)))

const token0Balance = ref(0)
const token1Balance = ref(0)

const token0Amount = ref(0)
const token1Amount = ref(0)

const token0AmountError = ref(false)

const blockHeight = computed(() => _block.blockHeight)
const publicKey = computed(() => _user.publicKey)

const refreshBalances = async () => {
  if (selectedToken0.value === constants.LINERA_NATIVE_ID) {
    token0Balance.value = userBalance.value
  } else {
    await meme.balanceOfMeme(token0Application.value, (balance: string) => {
      token0Balance.value = Number(Number(balance).toFixed(4))
    })
  }

  if (selectedToken1.value === constants.LINERA_NATIVE_ID) {
    token1Balance.value = userBalance.value
  } else {
    await meme.balanceOfMeme(token1Application.value, (balance: string) => {
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
}, { immediate: true, deep: true })

watch(blockHeight, async () => {
  await refreshBalances()
}, { immediate: true, deep: true })

watch(token0Chain, async () => {
  await refreshBalances()
}, { immediate: true, deep: true })

watch(token1Chain, async () => {
  await refreshBalances()
}, { immediate: true, deep: true })

watch(token0Amount, () => {
  const price = Number((selectedToken0.value === selectedPool.value?.token0 ? selectedPool.value?.token0Price : selectedPool.value?.token1Price) as string)
  setTimeout(() => {
    token1Amount.value = Number(((token0Amount.value * price) || 0).toFixed(4))
  }, 1000)
})

watch(token1Amount, () => {
  const price = Number((selectedToken1.value === selectedPool.value?.token1 ? selectedPool.value?.token1Price : selectedPool.value?.token0Price) as string)
  setTimeout(() => {
    token0Amount.value = Number(((token1Amount.value * price) || 0).toFixed(4))
  }, 1000)
})

const getLatestTransactions = () => {
  _pool.latestTransactions({
    startId: _pool.nextStartId(selectedPool.value.poolId)
  }, selectedPool.value.poolId, selectedPool.value.poolApplication as account.Account)
}

watch(publicKey, async () => {
  await refreshBalances()
}, { immediate: true, deep: true })

const onExchangeClick = () => {
  const token1 = selectedToken0.value
  _swap.selectedToken0 = selectedToken1.value
  _swap.selectedToken1 = token1
  token0Amount.value = 0
  token1Amount.value = 0
}

const onToken1MaxClick = () => {
  token1Amount.value = token1Balance.value
}

const onToken0MaxClick = () => {
  token0Amount.value = token0Balance.value
}

const onSwapClick = async () => {
  token0AmountError.value = token0Amount.value > token0Balance.value
  if (token0AmountError.value) return

  const variables = {
    amount0In: selectedToken0.value === selectedPool.value.token0 ? token0Amount.value.toString() : undefined,
    amount1In: selectedToken0.value === selectedPool.value.token1 ? token0Amount.value.toString() : undefined,
    amount0OutMin: undefined,
    amount1OutMin: undefined,
    to: undefined,
    blockTimestamp: undefined
  }
  const queryBytes = await lineraWasm.graphql_deserialize_pool_operation(SWAP.loc?.source?.body as string, stringify(variables) as string)
  return new Promise((resolve, reject) => {
    window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: account._Account.accountApplication(selectedPool.value.poolApplication as account.Account),
        publicKey: publicKey.value,
        query: {
          query: SWAP.loc?.source?.body,
          variables,
          applicationOperationBytes: queryBytes
        },
        operationName: 'createMeme'
      }
    }).then((hash) => {
      resolve(hash as string)
      void refreshBalances()
      getLatestTransactions()
      swap.getPools()
    }).catch((e) => {
      reject(e)
    })
  })
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
  margin: 8px 0 0 0
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
