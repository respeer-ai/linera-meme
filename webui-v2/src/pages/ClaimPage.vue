<template>
  <q-page class='row justify-center'>
    <main class='claim-page page-width q-py-xl'>
      <section class='claim-shell'>
        <header class='claim-page-header'>
          <h1 class='claim-title q-ma-none'>Claim</h1>
        </header>

        <q-card flat class='claim-card'>
          <template v-if='selectedPair'>
            <div class='claim-section claim-header'>
              <div class='claim-pair-wrap'>
                <pool-pair-logo
                  :token0-logo='tokenLogo(selectedPair.token0)'
                  :token1-logo='tokenLogo(selectedPair.token1)'
                  size='30px'
                  overlap='20px'
                  border-width='2px'
                />
                <div class='claim-pair-block'>
                  <div class='claim-pair'>{{ pairLabel }}</div>
                </div>
              </div>
            </div>

            <div v-if='selectedPool && walletConnected' class='claim-section claim-primary-section'>
              <div class='claim-token-list'>
                <button
                  v-for='entry in claimTokenEntries'
                  :key='entry.token'
                  type='button'
                  :class='["claim-token-option", { "claim-token-option-active": selectedToken === entry.token }]'
                  :disabled='loading || submitting'
                  @click='selectedToken = entry.token'
                >
                  <span class='claim-token-main'>
                    <q-avatar size='22px'>
                      <q-img :src='tokenLogo(entry.token)' fit='contain' />
                    </q-avatar>
                    <span>{{ tokenTicker(entry.token) }}</span>
                  </span>
                  <span class='claim-token-amount'>{{ formatAmount(entry.claimableAmount) }}</span>
                </button>
              </div>

              <div class='claim-balance-row q-mt-lg'>
                <div>
                  <div class='claim-label'>Claimable</div>
                  <div class='claim-balance'>{{ formatAmount(selectedClaimableAmount) }} <span class='claim-balance-unit'>{{ selectedTokenTicker }}</span></div>
                </div>
              </div>

              <q-input
                v-model='claimAmount'
                borderless
                dark
                type='number'
                step='0.0001'
                placeholder='0'
                input-class='claim-amount-input'
                class='q-mt-md claim-amount-field'
                :disable='submitting || loading'
              />

              <div class='claim-chips'>
                <q-btn
                  v-for='ratio in [10, 25, 50, 75, 100]'
                  :key='ratio'
                  outline
                  rounded
                  dense
                  no-caps
                  color='grey-5'
                  class='claim-chip'
                  :label='`${ratio}%`'
                  :disable='submitting || loading || !hasClaimableAmount'
                  @click='setRatio(ratio)'
                />
              </div>
            </div>

            <div v-else-if='selectedPool && !walletConnected' class='claim-empty'>
              <div class='claim-empty-title'>Wallet disconnected</div>
              <div class='claim-empty-text'>Connect your wallet to claim available balances.</div>
            </div>

            <div v-else class='claim-empty'>
              <div class='claim-empty-title'>Pool unavailable</div>
              <div class='claim-empty-text'>Return to positions and try again after pools finish loading.</div>
            </div>
          </template>

          <div v-else class='claim-empty'>
            <div class='claim-empty-title'>Pool unavailable</div>
            <div class='claim-empty-text'>Return to positions and try again after pools finish loading.</div>
          </div>
        </q-card>

        <q-btn
          rounded
          no-caps
          class='claim-action bg-primary text-white'
          :disable='submitDisabled'
          :loading='submitting || loading'
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
import { account, ams, kline, notify, swap, user, type meme } from 'src/stores/export'
import { constants } from 'src/constant'
import { NotifyType } from 'src/stores/notify'
import { Wallet } from 'src/wallet'
import ConnectWalletView from 'src/components/wallet/ConnectWalletView.vue'
import { resolveRoutePoolPair } from 'src/components/pools/poolFlow'
import PoolPairLogo from 'src/components/pools/PoolPairLogo.vue'
import { type ClaimBalanceEntry } from 'src/stores/kline'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'

interface ClaimTokenEntry {
  token: string
  claimableAmount: string
  balance: ClaimBalanceEntry | undefined
}

const route = useRoute()
const router = useRouter()

const connectingWallet = ref(false)
const submitting = ref(false)
const loading = ref(false)
const selectedToken = ref('')
const claimAmount = ref('')
const claimBalances = ref<ClaimBalanceEntry[]>([])

const walletConnected = computed(() => user.User.walletConnected())
const routePair = computed(() => resolveRoutePoolPair({
  token0: route.query.token0,
  token1: route.query.token1,
}))
const queryValue = (value: unknown) => {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}
const normalizeClaimToken = (token: string | undefined) => (
  token === 'native' || !token ? constants.LINERA_NATIVE_ID : token
)
const routeToken = computed(() => {
  const token = queryValue(route.query.token)
  return token ? normalizeClaimToken(token) : undefined
})
const routePoolApplication = computed(() => queryValue(route.query.poolApplication))
const selectedPool = computed(() => {
  if (!routePair.value) return undefined
  return swap.Swap.getVisiblePool(routePair.value.token0, routePair.value.token1)
})
const selectedPair = computed(() => {
  if (selectedPool.value) {
    return {
      token0: selectedPool.value.token0,
      token1: selectedPool.value.token1 || constants.LINERA_NATIVE_ID,
    }
  }
  if (!routePair.value) return undefined
  return {
    token0: routePair.value.token0,
    token1: routePair.value.token1,
  }
})
const poolApplication = (pool: Pool | undefined) => pool?.poolApplication as account.Account | undefined
const selectedPoolApplicationId = computed(() => (
  selectedPool.value
    ? account._Account.poolApplicationDescription(poolApplication(selectedPool.value))
    : undefined
))
const poolApplicationId = computed(() => routePoolApplication.value || selectedPoolApplicationId.value)
const tokenTicker = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_TICKER
  const application = ams.Ams.application(token)
  const memeSpec = JSON.parse(application?.spec || '{}') as meme.Meme
  return memeSpec?.ticker || token
}
const tokenLogo = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_LOGO
  const application = ams.Ams.application(token)
  return application ? ams.Ams.applicationLogo(application) : constants.LINERA_LOGO
}
const pairLabel = computed(() => selectedPair.value
  ? `${tokenTicker(selectedPair.value.token0)} / ${tokenTicker(selectedPair.value.token1)}`
  : 'Pool')
const balanceForToken = (token: string) => {
  const normalizedToken = normalizeClaimToken(token)
  return claimBalances.value.find((entry) => (
    entry.pool_application_id === poolApplicationId.value &&
    normalizeClaimToken(entry.token) === normalizedToken
  ))
}
const claimTokenEntries = computed<ClaimTokenEntry[]>(() => {
  if (!selectedPair.value) return []
  const tokens = Array.from(new Set([selectedPair.value.token0, selectedPair.value.token1].map(normalizeClaimToken)))
  return tokens.map((token) => {
    const balance = balanceForToken(token)
    return {
      token,
      claimableAmount: balance?.claimable_amount || '0',
      balance,
    }
  })
})
const selectedEntry = computed(() => claimTokenEntries.value.find((entry) => entry.token === selectedToken.value))
const selectedBalance = computed(() => selectedEntry.value?.balance)
const selectedClaimableAmount = computed(() => selectedEntry.value?.claimableAmount || '0')
const selectedClaimableNumber = computed(() => amountValue(selectedClaimableAmount.value))
const hasClaimableAmount = computed(() => selectedClaimableNumber.value > 0)
const claimAmountNumber = computed(() => amountValue(claimAmount.value))
const selectedTokenTicker = computed(() => tokenTicker(selectedToken.value))
const primaryActionLabel = computed(() => walletConnected.value ? 'CLAIM' : 'CONNECT WALLET')
const submitDisabled = computed(() => {
  if (!walletConnected.value) return false
  if (!selectedPool.value || loading.value || submitting.value) return true
  if (!selectedToken.value) return true
  if (selectedBalance.value?.projection_status === 'incomplete') return true
  return !(claimAmountNumber.value > 0 && claimAmountNumber.value <= selectedClaimableNumber.value)
})

const amountValue = (value: string | number | null | undefined) => {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  return Number.isFinite(numeric) ? numeric : 0
}
const formatAmount = (value: string | number) => {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  if (!Number.isFinite(numeric)) return '0'
  if (numeric === 0) return '0'
  if (numeric >= 1000) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    }).format(numeric)
  }
  if (numeric >= 1) return numeric.toFixed(6).replace(/\.?0+$/, '')
  return numeric.toFixed(8).replace(/\.?0+$/, '')
}
const formatClaimInputAmount = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return '0'
  const scaled = Math.floor(value * 10000) / 10000
  return scaled.toFixed(4).replace(/\.?0+$/, '')
}
const setRatio = (ratio: number) => {
  if (!selectedClaimableNumber.value) return
  claimAmount.value = formatClaimInputAmount(selectedClaimableNumber.value * ratio / 100)
}
const selectDefaultToken = () => {
  const routeEntry = routeToken.value
    ? claimTokenEntries.value.find((entry) => entry.token === routeToken.value)
    : undefined
  const claimableEntry = claimTokenEntries.value.find((entry) => amountValue(entry.claimableAmount) > 0)
  selectedToken.value = routeEntry?.token || claimableEntry?.token || claimTokenEntries.value[0]?.token || ''
}
const buildOwnerParam = async () => {
  const currentAccount = await user.User.account()
  if (!currentAccount.owner || !account._Account.chainId(currentAccount)) return ''
  return account._Account.accountDescription(currentAccount)
}
const loadClaimBalances = async () => {
  if (!walletConnected.value || !selectedPool.value) {
    claimBalances.value = []
    return
  }

  loading.value = true
  try {
    const owner = await buildOwnerParam()
    if (!owner) {
      claimBalances.value = []
      return
    }
    const response = await kline.Kline.getClaimBalances(owner)
    claimBalances.value = response?.balances || []
    selectDefaultToken()
    claimAmount.value = ''
  } finally {
    loading.value = false
  }
}
const refreshAfterClaim = async () => {
  await swap.Swap.getPools()
  await loadClaimBalances()
  void Wallet.getBalance()
}
const onPrimaryAction = async () => {
  if (!walletConnected.value) {
    connectingWallet.value = true
    return
  }

  if (submitDisabled.value || !selectedPool.value) return

  submitting.value = true
  try {
    await Wallet.claim(
      selectedPool.value,
      selectedToken.value,
      claimAmount.value,
      async () => {
        await refreshAfterClaim()
        notify.Notify.pushNotification({
          Title: 'Claim',
          Message: 'Claim submitted successfully.',
          Popup: true,
          Type: NotifyType.Success,
        })
        void router.push('/positions')
      },
      (e: string) => {
        notify.Notify.pushNotification({
          Title: 'Claim',
          Message: `Failed claim: ${e}`,
          Popup: true,
          Type: NotifyType.Error,
        })
      },
    )
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  ams.Ams.getApplications()
  await swap.Swap.getPools()
  await loadClaimBalances()
})

watch(
  () => [
    walletConnected.value,
    poolApplicationId.value,
    route.query.token,
  ],
  async ([connected, poolApplication, token], [previousConnected, previousPoolApplication, previousToken]) => {
    if (!connected || !poolApplication) return
    if (connected === previousConnected && poolApplication === previousPoolApplication && token === previousToken) return
    await loadClaimBalances()
  },
)
</script>

<style scoped lang='sass'>
.claim-page
  width: 100%
  display: flex
  justify-content: center

.claim-shell
  width: 100%
  max-width: 560px

.claim-page-header
  display: flex
  justify-content: center
  margin-bottom: 28px

.claim-title
  color: var(--q-light)
  font-size: 32px
  font-weight: 500
  line-height: 1.12
  letter-spacing: 0

.claim-card
  border: 1px solid rgba(255, 255, 255, 0.1)
  border-radius: 8px
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.025))
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.22)
  overflow: hidden

.claim-section
  padding: 20px

.claim-section + .claim-section
  border-top: 1px solid rgba(255, 255, 255, 0.08)

.claim-header
  display: flex
  align-items: center
  justify-content: flex-start
  gap: 16px
  background: rgba(0, 0, 0, 0.1)

.claim-primary-section
  padding-top: 18px

.claim-pair-wrap,
.claim-token-main
  display: flex
  align-items: center
  gap: 14px

.claim-pair-block
  display: flex
  flex-direction: column
  gap: 4px

.claim-pair
  font-size: 20px
  font-weight: 700
  color: var(--q-light)

.claim-label,
.claim-empty-text
  color: #9aa0ab

.claim-token-list
  display: grid
  gap: 10px
  margin-top: 10px

.claim-token-option
  width: 100%
  min-height: 48px
  display: flex
  align-items: center
  justify-content: space-between
  gap: 14px
  padding: 12px 14px
  border: 1px solid rgba(255, 255, 255, 0.08)
  border-radius: 8px
  background: rgba(0, 0, 0, 0.12)
  color: #d7dde7
  font-size: 15px
  cursor: pointer

.claim-token-option-active
  border-color: rgba(255, 255, 255, 0.26)
  background: rgba(255, 255, 255, 0.08)

.claim-token-option:disabled
  cursor: default
  opacity: 0.72

.claim-token-amount
  color: #9aa0ab

.claim-balance-row
  display: flex
  align-items: flex-end
  justify-content: space-between
  gap: 16px

.claim-balance
  margin-top: 4px
  font-size: 24px
  font-weight: 400
  color: #9aa0ab

.claim-balance-unit
  font-size: 13px
  font-weight: 400
  color: #9aa0ab

.claim-amount-field
  margin-top: 8px
  padding: 14px 16px
  border: 1px solid rgba(255, 255, 255, 0.08)
  border-radius: 8px
  background: rgba(0, 0, 0, 0.14)

.claim-amount-field :deep(.q-field__control)
  min-height: auto
  height: auto
  padding: 0
  background: transparent !important
  box-shadow: none !important

.claim-amount-field :deep(.q-field__native)
  padding: 0
  font-size: 36px
  line-height: 1.15
  font-weight: 700
  color: var(--q-light)

.claim-amount-field :deep(.q-field__native::placeholder)
  color: rgba(255, 255, 255, 0.28)

.claim-chips
  display: grid
  grid-template-columns: repeat(5, minmax(0, 1fr))
  gap: 10px
  margin-top: 16px

.claim-chip
  min-width: 0
  min-height: 30px
  padding-top: 0
  padding-bottom: 0
  border-color: rgba(255, 255, 255, 0.16) !important

.claim-chip :deep(.q-btn__content)
  font-size: 12px
  line-height: 1
  padding-top: 4px
  padding-bottom: 4px

.claim-empty-title
  font-size: 14px
  font-weight: 700
  color: #9aa0ab

.claim-empty
  padding: 20px

.claim-empty-text
  margin-top: 6px
  font-size: 14px
  line-height: 1.5

.claim-action
  width: 100%
  min-height: 50px
  margin-top: 24px
  font-size: 16px
  font-weight: 700
  letter-spacing: 0

@media (max-width: 599px)
  .claim-page
    padding-left: 16px
    padding-right: 16px

  .claim-title
    font-size: 28px
</style>
