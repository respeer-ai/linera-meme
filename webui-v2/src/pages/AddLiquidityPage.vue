<template>
  <q-page class='row justify-center'>
    <main class='page-width q-py-xl' style='max-width: 560px; width: 100%;'>
      <div class='text-h4 text-white text-center q-mb-xl'>Add Liquidity</div>

      <q-card flat class='bg-dark-secondary radius-16'>
        <div class='column'>
          <token-input-view
            label='Token 0'
            :tokens='tokenInputOptions'
            :disable='submitting'
            v-model='selectedToken0'
            v-model:amount='amount0'
          />
          <q-separator dark />
          <token-input-view
            label='Token 1'
            :tokens='token1InputOptions'
            :disable='submitting'
            :auto-focus='false'
            v-model='selectedToken1'
            v-model:amount='amount1'
          />
        </div>
      </q-card>

      <div class='row justify-center q-mt-xl'>
        <q-btn
          rounded
          class='bg-primary text-white'
          style='width: calc(100% - 48px); max-width: 512px;'
          :disable='submitDisabled'
          :loading='submitting'
          @click='onPrimaryAction'
        >
          {{ primaryActionLabel }}
        </q-btn>
      </div>
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
const submitting = ref(false)
const connectingWallet = ref(false)
const walletConnected = computed(() => user.User.walletConnected())

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
  return findPoolByPair(swap.Swap.pools(), {
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
  const submissionMode = resolveLiquiditySubmissionMode(swap.Swap.pools(), {
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
  const token0CreatorChain = proxy.Proxy.tokenCreatorChain(selectedCanonicalPair.value?.token0 as string)
  const token1CreatorChain = selectedCanonicalPair.value?.token1 === constants.LINERA_NATIVE_ID
    ? undefined
    : proxy.Proxy.tokenCreatorChain(selectedCanonicalPair.value?.token1 as string)

  if (!token0CreatorChain || (selectedCanonicalPair.value?.token1 !== constants.LINERA_NATIVE_ID && !token1CreatorChain)) {
    notify.Notify.pushNotification({
      Title: 'Add liquidity',
      Message: 'Failed resolve token creator chain for pool creation.',
      Popup: true,
      Type: NotifyType.Error,
    })
    submitting.value = false
    return
  }

  await Wallet.createPool(
    token0CreatorChain.chainId,
    selectedCanonicalPair.value?.token0 as string,
    token1CreatorChain?.chainId,
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
