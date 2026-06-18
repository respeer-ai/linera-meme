<template>
  <q-page class='row justify-center'>
    <main class='add-liquidity-page page-width q-py-xl'>
      <section class='add-shell'>
        <header class='add-header'>
          <h1 class='add-title q-ma-none'>Add Liquidity</h1>
        </header>

        <q-card flat class='add-card'>
          <div class='token-stack'>
            <token-input-view
              label='Token 0'
              :tokens='tokenInputOptions'
              :disable='inputsDisabled'
              v-model='selectedToken0'
              :amount='amount0'
              @update:amount='onAmount0Input'
              @balance='onBalance0Update'
            />
            <div class='token-divider' />
            <token-input-view
              label='Token 1'
              :tokens='token1InputOptions'
              :disable='inputsDisabled'
              :auto-focus='false'
              v-model='selectedToken1'
              :amount='amount1'
              @update:amount='onAmount1Input'
              @balance='onBalance1Update'
            />
          </div>
        </q-card>

        <q-btn
          rounded
          no-caps
          class='add-action bg-primary text-white'
          :disable='submitDisabled'
          :loading='submitting'
          @click='onPrimaryAction'
        >
          {{ primaryActionLabel }}
        </q-btn>
      </section>
    </main>
    <q-dialog v-model='connectingWallet'>
      <div class='bg-dark-secondary q-py-lg radius-16' style='min-width: 400px;'>
        <connect-wallet-view @done='connectingWallet = false' @error='connectingWallet = false' />
      </div>
    </q-dialog>
  </q-page>
</template>

<script setup lang='ts'>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ams, meme, notify, proxy, swap, user } from 'src/stores/export'
import { constants } from 'src/constant'
import { NotifyType } from 'src/stores/notify'
import { Wallet } from 'src/wallet'
import ConnectWalletView from 'src/components/wallet/ConnectWalletView.vue'
import TokenInputView from 'src/components/trade/TokenInputView.vue'
import { type Token } from 'src/components/trade/Token'
import {
  findPoolByPair,
  formatLiquidityInputAmount,
  linkedAddLiquidityAmount,
  mapPairAmountsToPoolOrder,
  normalizePoolPair,
  resolveLiquiditySubmissionMode,
  resolveRoutePoolPair,
} from 'src/components/pools/poolFlow'

const route = useRoute()
const router = useRouter()

const selectedToken0 = ref(undefined as unknown as Token)
const selectedToken1 = ref(undefined as unknown as Token)
const amount0 = ref('')
const amount1 = ref('')
const balance0 = ref('0')
const balance1 = ref('0')
const updatingBalance0 = ref(true)
const updatingBalance1 = ref(true)
const lastEditedAmountSide = ref<'amount0' | 'amount1' | undefined>(undefined)
const linkingAmounts = ref(false)
const submitting = ref(false)
const connectingWallet = ref(false)
const walletConnected = computed(() => user.User.walletConnected())
const inputsDisabled = computed(() => submitting.value || !walletConnected.value)

const tokenInputOptions = computed<Token[]>(() => {
  const memeOptions = ams.Ams.applications().map((application) => {
    const metadata = JSON.parse(application.spec) as meme.Meme
    return {
      ...application,
      meme: metadata,
    } as Token
  })

  return [
    {
      applicationId: constants.LINERA_NATIVE_ID,
      applicationName: constants.LINERA_TICKER,
      applicationType: 'native',
      creator: '',
      keyWords: [],
      logoStoreType: 0,
      logo: '',
      description: constants.LINERA_DESCRIPTION,
      spec: JSON.stringify({ ticker: constants.LINERA_TICKER }),
      createdAt: 0,
      meme: {
        ticker: constants.LINERA_TICKER,
      } as meme.Meme,
    } as unknown as Token,
    ...memeOptions,
  ]
})

const token1InputOptions = computed(() => {
  if (!selectedToken0.value?.applicationId) return tokenInputOptions.value
  return tokenInputOptions.value.filter((option) => option.applicationId !== selectedToken0.value.applicationId)
})

const selectedPool = computed(() => {
  if (!selectedToken0.value?.applicationId || !selectedToken1.value?.applicationId) return undefined
  return findPoolByPair(swap.Swap.visiblePools(), {
    token0: selectedToken0.value.applicationId,
    token1: selectedToken1.value.applicationId,
  })
})
const selectedCanonicalPair = computed(() => {
  if (!selectedToken0.value?.applicationId || !selectedToken1.value?.applicationId) return undefined
  return normalizePoolPair({
    token0: selectedToken0.value.applicationId,
    token1: selectedToken1.value.applicationId,
  })
})

const validationMessage = computed(() => {
  if (!selectedToken0.value?.applicationId || !selectedToken1.value?.applicationId) return 'Select both tokens.'
  if (selectedToken0.value.applicationId === selectedToken1.value.applicationId) return 'Select two different tokens.'
  if (Number(amount0.value) <= 0 || Number(amount1.value) <= 0) {
    return 'Input positive amounts for both tokens.'
  }
  return ''
})

const submitDisabled = computed(() => {
  return walletConnected.value && (submitting.value || validationMessage.value.length > 0)
})

const primaryActionLabel = computed(() => {
  return walletConnected.value ? 'ADD LIQUIDITY' : 'CONNECT WALLET'
})

const requestedRoutePair = computed(() => resolveRoutePoolPair({
  token0: route.query.token0,
  token1: route.query.token1,
}))

const capAmountByBalance = (amount: string, balance: string, updatingBalance = false) => {
  if (!walletConnected.value) return ''
  if (updatingBalance) return amount

  const amountValue = Number(amount)
  const balanceValue = Number(balance)
  if (!Number.isFinite(amountValue) || amountValue <= 0) return amount
  if (!Number.isFinite(balanceValue) || balanceValue <= 0) return ''
  return amountValue > balanceValue ? formatLiquidityInputAmount(balanceValue) : amount
}

const onBalance0Update = ({ balance, updating }: { balance: string; updating: boolean }) => {
  balance0.value = balance
  updatingBalance0.value = updating
}

const onBalance1Update = ({ balance, updating }: { balance: string; updating: boolean }) => {
  balance1.value = balance
  updatingBalance1.value = updating
}

const onAmount0Input = (value: string | undefined) => {
  amount0.value = capAmountByBalance(value === undefined ? '' : value, balance0.value, updatingBalance0.value)
  if (!linkingAmounts.value) lastEditedAmountSide.value = 'amount0'
}

const onAmount1Input = (value: string | undefined) => {
  amount1.value = capAmountByBalance(value === undefined ? '' : value, balance1.value, updatingBalance1.value)
  if (!linkingAmounts.value) lastEditedAmountSide.value = 'amount1'
}

const applyBalanceCaps = () => {
  if (linkingAmounts.value) return false

  const cappedAmount0 = capAmountByBalance(amount0.value, balance0.value, updatingBalance0.value)
  const cappedAmount1 = capAmountByBalance(amount1.value, balance1.value, updatingBalance1.value)
  if (cappedAmount0 === amount0.value && cappedAmount1 === amount1.value) return false

  linkingAmounts.value = true
  try {
    amount0.value = cappedAmount0
    amount1.value = cappedAmount1
  } finally {
    linkingAmounts.value = false
  }

  return true
}

const applyLinkedLiquidityAmount = () => {
  if (linkingAmounts.value) return
  if (!selectedPool.value || !selectedToken0.value?.applicationId || !selectedToken1.value?.applicationId) return
  if (!lastEditedAmountSide.value) return

  const sourceAmount = lastEditedAmountSide.value === 'amount0' ? amount0.value : amount1.value
  const sourceToken = lastEditedAmountSide.value === 'amount0'
    ? selectedToken0.value.applicationId
    : selectedToken1.value.applicationId
  const targetToken = lastEditedAmountSide.value === 'amount0'
    ? selectedToken1.value.applicationId
    : selectedToken0.value.applicationId
  const targetBalance = lastEditedAmountSide.value === 'amount0' ? balance1.value : balance0.value
  const updatingTargetBalance = lastEditedAmountSide.value === 'amount0' ? updatingBalance1.value : updatingBalance0.value
  const linkedAmount = linkedAddLiquidityAmount({
    pool: selectedPool.value,
    sourceToken,
    targetToken,
    sourceAmount,
    ...(updatingTargetBalance ? {} : { maxTargetAmount: targetBalance }),
  })

  linkingAmounts.value = true
  try {
    if (lastEditedAmountSide.value === 'amount0') {
      amount1.value = linkedAmount
    } else {
      amount0.value = linkedAmount
    }
  } finally {
    linkingAmounts.value = false
  }
}

watch([amount0, amount1, balance0, balance1, updatingBalance0, updatingBalance1, walletConnected, selectedPool, selectedToken0, selectedToken1], () => {
  if (applyBalanceCaps()) return
  applyLinkedLiquidityAmount()
})

watch(selectedToken0, () => {
  if (
    selectedToken1.value?.applicationId &&
    selectedToken0.value?.applicationId === selectedToken1.value.applicationId
  ) {
    selectedToken1.value = undefined as unknown as Token
  }
})

const initializeDefaultTokens = () => {
  if (requestedRoutePair.value) return
  if (!tokenInputOptions.value.length) return

  const nativeToken = tokenInputOptions.value.find((token) => token.applicationId === constants.LINERA_NATIVE_ID)
  const firstNonNativeToken = tokenInputOptions.value.find((token) => token.applicationId !== constants.LINERA_NATIVE_ID)

  if (!selectedToken0.value?.applicationId || selectedToken0.value.applicationId === selectedToken1.value?.applicationId) {
    selectedToken0.value = (nativeToken || tokenInputOptions.value[0]) as Token
  }

  const token1Options = tokenInputOptions.value.filter(
    (token) => token.applicationId !== selectedToken0.value?.applicationId,
  )
  const preferredToken1 = token1Options.find((token) => token.applicationId === firstNonNativeToken?.applicationId)

  if (
    !selectedToken1.value?.applicationId ||
    selectedToken1.value.applicationId === selectedToken0.value?.applicationId
  ) {
    selectedToken1.value = (preferredToken1 || token1Options[0]) as Token
  }
}

const initializeFromRoute = () => {
  if (!requestedRoutePair.value) {
    initializeDefaultTokens()
    return
  }

  selectedToken0.value = tokenInputOptions.value.find((token) => token.applicationId === requestedRoutePair.value?.token0) as Token
  selectedToken1.value = tokenInputOptions.value.find((token) => token.applicationId === requestedRoutePair.value?.token1) as Token
}

const onAddLiquidity = async () => {
  if (submitDisabled.value) return

  submitting.value = true
  const account = await user.User.account()
  const submissionMode = resolveLiquiditySubmissionMode(swap.Swap.visiblePools(), {
    token0: selectedToken0.value.applicationId,
    token1: selectedToken1.value.applicationId,
  })

  if (submissionMode === 'add-liquidity' && selectedPool.value) {
    const orderedAmounts = mapPairAmountsToPoolOrder({
      selectedToken0: selectedToken0.value.applicationId,
      selectedToken1: selectedToken1.value.applicationId,
      amountForSelectedToken0: amount0.value,
      amountForSelectedToken1: amount1.value,
      canonicalPair: {
        token0: selectedPool.value.token0,
        token1: selectedPool.value.token1 || constants.LINERA_NATIVE_ID,
      },
    })

    await Wallet.addLiquidity(
      selectedPool.value,
      orderedAmounts.amount0,
      orderedAmounts.amount1,
      account,
      async () => {
        await swap.Swap.getPools()
        notify.Notify.pushNotification({
          Title: 'Add liquidity',
          Message: 'Add liquidity submitted successfully.',
          Popup: true,
          Type: NotifyType.Success,
        })
        submitting.value = false
        void router.push('/explore')
      },
      (e: string) => {
        notify.Notify.pushNotification({
          Title: 'Add liquidity',
          Message: `Failed add liquidity: ${e}`,
          Popup: true,
          Type: NotifyType.Error,
        })
        submitting.value = false
      },
    )
    return
  }

  const orderedAmounts = mapPairAmountsToPoolOrder({
    selectedToken0: selectedToken0.value.applicationId,
    selectedToken1: selectedToken1.value.applicationId,
    amountForSelectedToken0: amount0.value,
    amountForSelectedToken1: amount1.value,
    canonicalPair: {
      token0: selectedCanonicalPair.value?.token0 as string,
      token1: selectedCanonicalPair.value?.token1 as string,
    },
  })
  await Wallet.createPool(
    selectedCanonicalPair.value?.token0 as string,
    selectedCanonicalPair.value?.token1 === constants.LINERA_NATIVE_ID
      ? undefined
      : selectedCanonicalPair.value?.token1,
    orderedAmounts.amount0,
    orderedAmounts.amount1,
    account,
    async () => {
      await swap.Swap.getPools()
      notify.Notify.pushNotification({
        Title: 'Add liquidity',
        Message: 'Pool creation and initial liquidity submitted successfully.',
        Popup: true,
        Type: NotifyType.Success,
      })
      submitting.value = false
      void router.push('/explore')
    },
    (e: string) => {
      notify.Notify.pushNotification({
        Title: 'Add liquidity',
        Message: `Failed add liquidity: ${e}`,
        Popup: true,
        Type: NotifyType.Error,
      })
      submitting.value = false
    },
  )
}

const onPrimaryAction = () => {
  if (!walletConnected.value) {
    connectingWallet.value = true
    return
  }

  void onAddLiquidity()
}

onMounted(async () => {
  proxy.Proxy.getMemeApplications()
  ams.Ams.getApplications()
  await swap.Swap.getPools()
  initializeFromRoute()
})

watch(tokenInputOptions, () => {
  initializeFromRoute()
}, { deep: false })
</script>

<style scoped lang='sass'>
.add-liquidity-page
  width: 100%
  display: flex
  justify-content: center

.add-shell
  width: 100%
  max-width: 560px

.add-header
  display: flex
  justify-content: center
  margin-bottom: 28px

.add-title
  color: var(--q-light)
  font-size: 32px
  font-weight: 500
  line-height: 1.12
  letter-spacing: 0

.add-card
  border: 1px solid rgba(255, 255, 255, 0.1)
  border-radius: 8px
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.025))
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.22)
  overflow: hidden

.token-stack
  display: grid
  gap: 0

.token-divider
  height: 1px
  margin: 0 18px
  background: rgba(255, 255, 255, 0.08)

.add-action
  width: 100%
  min-height: 50px
  margin-top: 24px
  font-size: 16px
  font-weight: 700
  letter-spacing: 0

@media (max-width: 599px)
  .add-liquidity-page
    padding-left: 16px
    padding-right: 16px

  .add-title
    font-size: 28px
</style>
