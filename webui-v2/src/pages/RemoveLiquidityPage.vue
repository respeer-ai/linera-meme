<template>
  <q-page class='row justify-center'>
    <main class='page-width q-py-xl' style='max-width: 560px; width: 100%;'>
      <div class='text-h4 text-white text-center q-mb-xl'>Remove Liquidity</div>

      <q-card flat class='bg-dark-secondary radius-16'>
        <template v-if='selectedPair'>
          <div class='remove-section remove-header'>
            <div class='remove-pair-wrap'>
              <pool-pair-logo
                :token0-logo='tokenLogo(selectedPair.token0)'
                :token1-logo='tokenLogo(selectedPair.token1)'
                size='30px'
                overlap='20px'
                border-width='2px'
              />
              <div class='remove-pair-block'>
                <div class='remove-pair'>{{ pairLabel }}</div>
              </div>
            </div>
          </div>

          <div v-if='selectedPool && walletConnected' class='remove-section remove-primary-section'>
            <div class='remove-balance-row'>
              <div>
                <div class='remove-label'>Available</div>
                <div class='remove-balance'>{{ formatAmount(currentLiquidity.liquidity) }} <span class='remove-balance-unit'>LMM</span></div>
              </div>
            </div>

            <q-input
              v-model='removeAmount'
              borderless
              dark
              type='number'
              placeholder='0'
              input-class='remove-amount-input'
              class='q-mt-md remove-amount-field'
              :disable='submitting || liquidityLoading'
            />

            <div class='remove-chips'>
              <q-btn
                v-for='ratio in [10, 25, 50, 75, 100]'
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
          </div>

          <div v-if='selectedPool && walletConnected' class='remove-section'>
            <div class='remove-estimate-title'>You Receive</div>
            <div class='remove-estimate-list'>
              <div class='remove-estimate-row'>
                <span class='remove-estimate-token'>
                  <q-avatar size='20px'>
                    <q-img :src='tokenLogo(selectedPool.token0)' fit='contain' />
                  </q-avatar>
                  <span>{{ tokenTicker(selectedPool.token0) }}</span>
                </span>
                <span>{{ formatAmount(estimatedAmount0) }}</span>
              </div>
              <div class='remove-estimate-row'>
                <span class='remove-estimate-token'>
                  <q-avatar size='20px'>
                    <q-img :src='tokenLogo(selectedPool.token1 || constants.LINERA_NATIVE_ID)' fit='contain' />
                  </q-avatar>
                  <span>{{ tokenTicker(selectedPool.token1 || constants.LINERA_NATIVE_ID) }}</span>
                </span>
                <span>{{ formatAmount(estimatedAmount1) }}</span>
              </div>
            </div>
          </div>

          <div v-else class='remove-empty'>
            <div class='remove-empty-title'>Pool unavailable</div>
            <div class='remove-empty-text'>
              Return to positions and try again after pools finish loading.
            </div>
          </div>
        </template>

        <div v-else class='remove-empty'>
          <div class='remove-empty-title'>Pool unavailable</div>
          <div class='remove-empty-text'>
            Return to positions and try again after pools finish loading.
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ams, notify, pool, swap, user, type meme } from 'src/stores/export'
import { constants } from 'src/constant'
import { type LiquidityAmount } from 'src/stores/pool'
import { NotifyType } from 'src/stores/notify'
import { Wallet } from 'src/wallet'
import ConnectWalletView from 'src/components/wallet/ConnectWalletView.vue'
import { resolveRoutePoolPair } from 'src/components/pools/poolFlow'
import PoolPairLogo from 'src/components/pools/PoolPairLogo.vue'

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
const tokenLogo = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_LOGO
  const application = ams.Ams.application(token)
  return application ? ams.Ams.applicationLogo(application) : constants.LINERA_LOGO
}
const pairLabel = computed(() => selectedPair.value
  ? `${tokenTicker(selectedPair.value.token0)} / ${tokenTicker(selectedPair.value.token1)}`
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
  ams.Ams.getApplications()
  await swap.Swap.getPools()
  await loadLiquidity()
})

watch(
  () => [walletConnected.value, selectedPool.value?.poolApplication],
  async ([connected, poolApplication], [previousConnected, previousPoolApplication]) => {
    if (!connected || !poolApplication) return
    if (connected === previousConnected && poolApplication === previousPoolApplication) return
    await loadLiquidity()
  },
)
</script>

<style scoped lang='sass'>
.remove-section
  padding: 20px

.remove-header
  display: flex
  align-items: center
  justify-content: flex-start
  gap: 16px

.remove-primary-section
  padding-top: 10px

.remove-pair-wrap
  display: flex
  align-items: center
  gap: 14px

.remove-pair-block
  display: flex
  flex-direction: column
  gap: 4px

.remove-pair
  font-size: 20px
  font-weight: 700
  color: var(--q-light)

.remove-label,
.remove-empty-text
  color: #9aa0ab

.remove-balance-row
  display: flex
  align-items: flex-end
  justify-content: space-between
  gap: 16px

.remove-balance
  margin-top: 4px
  font-size: 24px
  font-weight: 400
  color: #9aa0ab

.remove-balance-unit
  font-size: 13px
  font-weight: 400
  color: #9aa0ab

.remove-amount-field
  margin-top: 8px

.remove-amount-field :deep(.q-field__control)
  min-height: auto
  height: auto
  padding: 0
  background: transparent !important
  box-shadow: none !important

.remove-amount-field :deep(.q-field__native)
  padding: 0
  font-size: 36px
  line-height: 1.15
  font-weight: 700
  color: var(--q-light)

.remove-amount-field :deep(.q-field__native::placeholder)
  color: rgba(255, 255, 255, 0.28)

.remove-chips
  display: flex
  flex-wrap: wrap
  gap: 10px
  margin-top: 16px

.remove-chip
  min-width: 58px
  min-height: 24px
  padding-top: 0
  padding-bottom: 0

.remove-chip :deep(.q-btn__content)
  font-size: 12px
  line-height: 1

.remove-chip :deep(.q-btn__content)
  padding-top: 4px
  padding-bottom: 4px

.remove-estimate-title,
.remove-empty-title
  font-size: 14px
  font-weight: 700
  color: #9aa0ab

.remove-estimate-list
  margin-top: 10px

.remove-estimate-row
  display: flex
  justify-content: space-between
  gap: 12px
  padding: 12px 0
  font-size: 15px
  color: #d7dde7

.remove-estimate-token
  display: inline-flex
  align-items: center
  gap: 8px

.remove-estimate-row + .remove-estimate-row
  border-top: 1px dashed rgba(255, 255, 255, 0.2)

.remove-empty
  padding: 20px

.remove-empty-text
  margin-top: 6px
  font-size: 14px
  line-height: 1.5
</style>
