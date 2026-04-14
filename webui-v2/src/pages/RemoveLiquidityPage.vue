<template>
  <q-page class='row justify-center'>
    <main class='page-width q-py-xl remove-page'>
      <div class='text-h4 text-white text-center q-mb-lg'>Manage Position</div>

      <q-card flat class='bg-dark-secondary radius-16 remove-card'>
        <div class='remove-card-header'>
          <div>
            <div class='remove-pair'>{{ pairLabel }}</div>
            <div class='remove-subtitle'>Redeem liquidity from this pool.</div>
          </div>
          <q-btn flat round dense icon='close' color='grey-5' @click='onBack' />
        </div>

        <template v-if='selectedPool && walletConnected'>
          <div class='remove-balance-row'>
            <div>
              <div class='remove-label'>Your liquidity share</div>
              <div class='remove-balance'>{{ formatAmount(currentLiquidity.liquidity) }} LMM</div>
            </div>
            <q-btn flat dense no-caps class='text-primary' label='Max' @click='fillMax' />
          </div>

          <q-input
            v-model='removeAmount'
            standout='bg-dark'
            dark
            label='LMM to redeem'
            class='q-mt-md'
            :disable='submitting || liquidityLoading'
          />

          <div class='remove-chips'>
            <q-btn
              v-for='ratio in [25, 50, 75, 100]'
              :key='ratio'
              outline
              rounded
              dense
              no-caps
              color='grey-5'
              class='remove-chip'
              :label='`${ratio}%`'
              :disable='submitting || liquidityLoading || !hasLiquidity'
              @click='setRatio(ratio)'
            />
          </div>

          <div class='remove-estimate'>
            <div class='remove-estimate-title'>Estimated received</div>
            <div class='remove-estimate-row'>
              <span>{{ tokenTicker(selectedPool.token0) }}</span>
              <span>{{ formatAmount(estimatedAmount0) }}</span>
            </div>
            <div class='remove-estimate-row'>
              <span>{{ tokenTicker(selectedPool.token1 || constants.LINERA_NATIVE_ID) }}</span>
              <span>{{ formatAmount(estimatedAmount1) }}</span>
            </div>
          </div>

          <div class='remove-note'>
            Redeeming burns part of your LMM share and returns the corresponding pool assets at the current reserve ratio.
          </div>
        </template>

        <div v-else class='remove-empty'>
          <div class='remove-empty-title'>Pool unavailable</div>
          <div class='remove-empty-text'>
            This position cannot be managed right now. Return to positions and try again after pools finish loading.
          </div>
        </div>
      </q-card>

      <div class='row justify-center q-mt-xl'>
        <q-btn
          rounded
          class='bg-primary text-white'
          style='width: calc(100% - 48px); max-width: 512px;'
          :disable='submitDisabled'
          :loading='submitting || liquidityLoading'
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ams, notify, pool, swap, user, type meme } from 'src/stores/export'
import { constants } from 'src/constant'
import { type LiquidityAmount } from 'src/stores/pool'
import { NotifyType } from 'src/stores/notify'
import { Wallet } from 'src/wallet'
import ConnectWalletView from 'src/components/wallet/ConnectWalletView.vue'
import { resolveRoutePoolPair } from 'src/components/pools/poolFlow'

const route = useRoute()
const router = useRouter()

const connectingWallet = ref(false)
const submitting = ref(false)
const liquidityLoading = ref(false)
const currentLiquidity = ref<LiquidityAmount>({
  liquidity: '0',
  amount0: '0',
  amount1: '0',
})
const removeAmount = ref('')

const walletConnected = computed(() => user.User.walletConnected())
const routePair = computed(() => resolveRoutePoolPair({
  token0: route.query.token0,
  token1: route.query.token1,
}))
const selectedPool = computed(() => {
  if (!routePair.value) return undefined
  return swap.Swap.getPool(routePair.value.token0, routePair.value.token1)
})
const hasLiquidity = computed(() => Number(removeAmountMax.value) > 0)
const removeAmountMax = computed(() => Number.parseFloat(currentLiquidity.value.liquidity || '0'))
const removeAmountNumber = computed(() => Number.parseFloat(removeAmount.value || '0'))
const removeRatio = computed(() => {
  if (!removeAmountMax.value || removeAmountMax.value <= 0) return 0
  return Math.min(Math.max(removeAmountNumber.value / removeAmountMax.value, 0), 1)
})
const estimatedAmount0 = computed(() => Number.parseFloat(currentLiquidity.value.amount0 || '0') * removeRatio.value)
const estimatedAmount1 = computed(() => Number.parseFloat(currentLiquidity.value.amount1 || '0') * removeRatio.value)
const tokenTicker = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_TICKER
  const application = ams.Ams.application(token)
  const memeSpec = JSON.parse(application?.spec || '{}') as meme.Meme
  return memeSpec?.ticker || token
}
const pairLabel = computed(() => selectedPool.value
  ? `${tokenTicker(selectedPool.value.token0)} / ${tokenTicker(selectedPool.value.token1 || constants.LINERA_NATIVE_ID)}`
  : 'Position')
const primaryActionLabel = computed(() => walletConnected.value ? 'REMOVE LIQUIDITY' : 'CONNECT WALLET')
const submitDisabled = computed(() => {
  if (!walletConnected.value) return false
  if (!selectedPool.value || submitting.value || liquidityLoading.value) return true
  if (!hasLiquidity.value) return true
  return !(removeAmountNumber.value > 0 && removeAmountNumber.value <= removeAmountMax.value)
})

const formatAmount = (value: string | number) => {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  if (!Number.isFinite(numeric)) return '0'
  if (numeric === 0) return '0'
  if (numeric >= 1) return numeric.toFixed(6).replace(/\.?0+$/, '')
  return numeric.toFixed(8).replace(/\.?0+$/, '')
}

const fillMax = () => {
  removeAmount.value = currentLiquidity.value.liquidity || '0'
}

const setRatio = (ratio: number) => {
  if (!removeAmountMax.value) return
  removeAmount.value = (removeAmountMax.value * ratio / 100).toFixed(18).replace(/\.?0+$/, '')
}

const loadLiquidity = async () => {
  if (!walletConnected.value || !selectedPool.value) return

  liquidityLoading.value = true
  const account = await user.User.account()

  pool.liquidity(account, selectedPool.value.poolApplication, (liquidity) => {
    liquidityLoading.value = false
    currentLiquidity.value = liquidity || {
      liquidity: '0',
      amount0: '0',
      amount1: '0',
    }
  })
}

const onBack = () => {
  void router.push('/positions')
}

const onPrimaryAction = async () => {
  if (!walletConnected.value) {
    connectingWallet.value = true
    return
  }

  if (submitDisabled.value || !selectedPool.value) return

  submitting.value = true
  const account = await user.User.account()
  await Wallet.removeLiquidity(
    selectedPool.value,
    removeAmount.value,
    account,
    async () => {
      await swap.Swap.getPools()
      await loadLiquidity()
      notify.Notify.pushNotification({
        Title: 'Remove liquidity',
        Message: 'Remove liquidity submitted successfully.',
        Popup: true,
        Type: NotifyType.Success,
      })
      submitting.value = false
      void router.push('/positions')
    },
    (e: string) => {
      notify.Notify.pushNotification({
        Title: 'Remove liquidity',
        Message: `Failed remove liquidity: ${e}`,
        Popup: true,
        Type: NotifyType.Error,
      })
      submitting.value = false
    },
  )
}

onMounted(async () => {
  await swap.Swap.getPools()
  await loadLiquidity()
})
</script>

<style scoped lang='sass'>
.remove-page
  max-width: 560px
  width: 100%

.remove-card
  padding: 20px

.remove-card-header
  display: flex
  align-items: flex-start
  justify-content: space-between
  gap: 16px

.remove-pair
  font-size: 22px
  font-weight: 700
  color: var(--q-light)

.remove-subtitle,
.remove-label,
.remove-note,
.remove-empty-text
  color: #9aa0ab

.remove-subtitle
  margin-top: 6px
  font-size: 14px

.remove-balance-row
  display: flex
  align-items: flex-end
  justify-content: space-between
  gap: 16px
  margin-top: 22px

.remove-balance
  margin-top: 4px
  font-size: 30px
  font-weight: 600
  color: var(--q-light)

.remove-chips
  display: flex
  flex-wrap: wrap
  gap: 10px
  margin-top: 16px

.remove-chip
  min-width: 64px

.remove-estimate
  margin-top: 20px
  padding: 14px 16px
  border: 1px solid rgba(255, 255, 255, 0.08)
  border-radius: 14px
  background: rgba(255, 255, 255, 0.02)

.remove-estimate-title,
.remove-empty-title
  font-size: 14px
  font-weight: 700
  color: var(--q-light)

.remove-estimate-row
  display: flex
  justify-content: space-between
  gap: 12px
  margin-top: 10px
  font-size: 14px
  color: #d7dde7

.remove-note
  margin-top: 16px
  font-size: 13px
  line-height: 1.5

.remove-empty
  margin-top: 24px
  padding: 18px
  border: 1px solid rgba(255, 255, 255, 0.08)
  border-radius: 14px

.remove-empty-text
  margin-top: 6px
  font-size: 14px
  line-height: 1.5
</style>
