<template>
  <q-page class='row justify-center'>
    <main class='page-width positions-page'>
      <section class='main-column'>
        <div class='reward-card'>
          <div class='reward-hero'>
            <div class='reward-copy'>
              <div class='reward-value-row'>
                <div class='reward-value'>
                  <span>{{ formattedLiquidityShare }}</span>
                  <span class='reward-unit'>LMM</span>
                  <q-img class='reward-inline-logo' :src='constants.MICROMEME_LOGO' width='18px' height='18px' fit='contain' />
                </div>
                <div class='reward-native-value'>
                  <span>{{ currentValueSummary.label }}</span>
                  <q-img class='reward-native-logo' :src='constants.LINERA_LOGO' width='18px' height='18px' fit='contain' />
                </div>
              </div>
              <div class='reward-label'>
                LMM liquidity share
                <span class='reward-info'>i
                  <q-tooltip class='reward-tooltip' anchor='top middle' self='bottom middle'>
                    <p>LMM tracks your liquidity share, not a tradable token.</p>
                    <p>Holding LMM lets you redeem liquidity and earn swap fees.</p>
                  </q-tooltip>
                </span>
              </div>
            </div>
          </div>

        </div>

        <section class='positions-section'>
          <div class='positions-header'>
            <h1 class='positions-title q-ma-none'>Your positions</h1>

            <div class='filter-row'>
              <button class='filter-btn filter-btn-primary' @click='onNewPositionClick'>
                <span class='filter-plus'>+</span>
                <span>New</span>
              </button>
              <button class='filter-btn'>
                <span>{{ selectedStatusLabel }}</span>
                <span class='filter-caret'>⌄</span>
                <q-menu class='status-menu' anchor='bottom right' self='top right' :offset='[0, 10]'>
                  <q-list dense class='status-menu-list'>
                    <q-item
                      v-for='option in statusOptions'
                      :key='option.value'
                      clickable
                      v-close-popup
                      class='status-menu-item'
                      @click='selectedStatus = option.value'
                    >
                      <q-item-section>{{ option.label }}</q-item-section>
                    </q-item>
                  </q-list>
                </q-menu>
              </button>
            </div>
          </div>

          <div v-if='positionsStore.loading && !positionsStore.loaded' class='positions-list'>
            <div v-for='index in 2' :key='index' class='position-card position-card-loading'>
              <q-skeleton dark type='text' width='32%' />
              <q-skeleton dark type='text' width='18%' />
              <div class='position-summary-row' :style='{ "--position-summary-columns": "4" }'>
                <q-skeleton dark type='text' width='100%' />
                <q-skeleton dark type='text' width='100%' />
                <q-skeleton dark type='text' width='100%' />
                <q-skeleton dark type='text' width='100%' />
              </div>
            </div>
          </div>

          <div v-else-if='visiblePositions.length' class='positions-list'>
            <article v-for='position in visiblePositions' :key='positionKey(position)' class='position-card'>
              <div class='position-card-header'>
                <div class='position-pair-wrap'>
                  <pool-pair-logo
                    :token0-logo='tokenLogo(position.token_0)'
                    :token1-logo='tokenLogo(position.token_1)'
                    size='30px'
                    overlap='20px'
                    border-width='2px'
                  />
                  <div>
                    <div class='position-pair'>{{ tokenTicker(position.token_0) }} / {{ tokenTicker(position.token_1) }}</div>
                  </div>
                </div>
                <div class='position-header-actions'>
                  <button v-if='positionActionLabel(position)' class='position-menu-btn' aria-label='Position actions'>
                    ⋮
                    <q-menu class='status-menu position-actions-menu' anchor='bottom right' self='top right' :offset='[0, 10]'>
                      <q-list dense class='status-menu-list'>
                        <q-item
                          clickable
                          v-close-popup
                          class='status-menu-item'
                          :disable='!canUsePositionAction(position)'
                          @click='onManagePositionClick(position)'
                        >
                          <q-item-section>{{ positionActionLabel(position) }}</q-item-section>
                        </q-item>
                      </q-list>
                    </q-menu>
                  </button>
                  <span :class='["position-badge", `position-badge-${position.status}`]'>
                    {{ positionStatusLabel(position.status) }}
                  </span>
                </div>
              </div>

              <div
                class='position-summary-row'
                :style='{ "--position-summary-columns": "4" }'
              >
                <div class='position-metric'>
                  <span class='metric-label'>Pool share</span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ positionPoolShareLabel(position) }}</span>
                    <span>{{ formatLiquidity(positionDisplayLiquidity(position).liquidity) }} LMM</span>
                  </span>
                </div>
                <div class='position-metric'>
                  <span class='metric-label'>Pooled tokens</span>
                  <span class='metric-value metric-value-stack'>
                    <span class='pooled-token-line'>
                      <span>{{ pooledTokenLabel(position, position.token_0) }}</span>
                      <span v-if='pooledTokenIncludesVirtual(position, position.token_0)' class='virtual-bootstrap-tag'>Includes virtual</span>
                    </span>
                    <span class='pooled-token-line'>
                      <span>{{ pooledTokenLabel(position, position.token_1) }}</span>
                      <span v-if='pooledTokenIncludesVirtual(position, position.token_1)' class='virtual-bootstrap-tag'>Includes virtual</span>
                    </span>
                  </span>
                </div>
                <div class='position-metric'>
                  <span class='metric-label'>
                    Trading Fees
                    <span v-if='hasMetricsWarning(position)' class='metric-warning'>!
                      <q-tooltip class='reward-tooltip' anchor='top middle' self='bottom middle'>
                        {{ metricsWarningMessage(position) }}
                      </q-tooltip>
                    </span>
                  </span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ positionFeesLabel(position).token0 }}</span>
                    <span>{{ positionFeesLabel(position).token1 }}</span>
                  </span>
                </div>
                <div class='position-metric'>
                  <span class='metric-label'>APR</span>
                  <span class='metric-value'>{{ positionAprLabel(position) }}</span>
                </div>
              </div>

              <div class='position-actions'>
              </div>
            </article>
          </div>

          <div v-else class='empty-card'>
            <div class='empty-icon-wrap'>
              <div class='empty-icon'>≈</div>
            </div>
            <div class='empty-title'>{{ emptyStateTitle }}</div>
            <div class='empty-text'>{{ emptyStateText }}</div>
            <div class='empty-actions'>
              <button class='empty-btn empty-btn-secondary' @click='onExplorePoolsClick'>Explore pools</button>
              <button class='empty-btn empty-btn-primary' @click='onNewPositionClick'>New position</button>
            </div>
          </div>

          <div v-if='showClosedHint' class='notice-row'>
            <div class='notice-icon'>i</div>
            <div class='notice-copy'>
              <div class='notice-title'>Looking for your closed positions?</div>
              <div class='notice-text'>Switch the filter to Closed to review positions you already redeemed.</div>
            </div>
          </div>

        </section>
      </section>
    </main>
  </q-page>
</template>

<script setup lang='ts'>
import axios from 'axios'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMeta } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { usePageSeo } from 'src/utils/seo'
import { constants } from 'src/constant'
import { buildRemoveLiquidityRoute } from 'src/components/pools/poolFlow'
import { useUserStore } from 'src/stores/user'
import { usePositionsStore, type Position, type PositionStatusFilter, type PositionsResponse } from 'src/stores/positions'
import { type PositionMetricsEntry, type PositionsInvalidationPayload } from 'src/stores/kline'
import { account, ams, kline, swap, type meme } from 'src/stores/export'
import { protocol } from 'src/utils'
import PoolPairLogo from 'src/components/pools/PoolPairLogo.vue'
import {
  canUsePositionAction as resolveCanUsePositionAction,
  isVirtualPosition,
  positionActionLabel as resolvePositionActionLabel,
  positionKey,
  positionDisplayLiquidityAmounts,
  positionDisplayShareRatio,
  positionHasVirtualReference,
  positionMetricsFor,
  positionMetricsKey,
  selectDisplayPositions,
  selectRewardPositions,
  virtualPositionMetricsFor,
} from './positionsData'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const positionsStore = usePositionsStore()

const selectedStatus = ref<PositionStatusFilter>('active')
const owner = ref('')
const summaryPositions = ref<Position[]>([])
const summaryPositionsRequestSerial = ref(0)
const summaryPositionMetricsSnapshots = ref<Record<string, PositionMetricsEntry>>({})
const positionsRefreshTimer = ref<number | undefined>(undefined)

const statusOptions: Array<{ value: PositionStatusFilter; label: string }> = [
  { value: 'all', label: 'All positions' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
]

const selectedStatusLabel = computed(() => (
  statusOptions.find((option) => option.value === selectedStatus.value)?.label || 'Status'
))
const walletConnected = computed(() => Boolean(userStore.chainId && userStore.publicKey))
const allPositions = computed(() => positionsStore.positions)
const visiblePositions = computed(() => selectDisplayPositions(allPositions.value))
const pools = computed(() => swap.Swap.pools())
const nativePriceMap = computed(() => protocol.buildNativePriceMap(pools.value))
const positionMetricsSnapshots = ref<Record<string, PositionMetricsEntry>>({})
const positionMetricsRequestSerial = ref(0)
const showClosedHint = computed(() => (
  walletConnected.value &&
  positionsStore.loaded &&
  !positionsStore.loading &&
  !allPositions.value.length &&
  selectedStatus.value !== 'closed'
))
const emptyStateTitle = computed(() => {
  if (!walletConnected.value) return 'Connect wallet to view positions'
  if (selectedStatus.value === 'closed') return 'No closed positions'
  return 'No positions'
})
const emptyStateText = computed(() => {
  if (!walletConnected.value) {
    return 'Connect your wallet to load liquidity positions associated with your account.'
  }
  if (selectedStatus.value === 'closed') {
    return 'You have not fully redeemed any liquidity positions yet.'
  }
  return 'You do not have any liquidity positions for the selected filter yet.'
})

const buildOwnerParam = async () => {
  const currentAccount = await userStore.account()
  if (!currentAccount.owner || !account._Account.chainId(currentAccount)) return ''
  return account._Account.accountDescription(currentAccount)
}

const refreshPositions = async () => {
  if (!walletConnected.value) {
    owner.value = ''
    summaryPositions.value = []
    summaryPositionMetricsSnapshots.value = {}
    positionMetricsSnapshots.value = {}
    positionsStore.clear()
    return
  }

  const nextOwner = await buildOwnerParam()
  owner.value = nextOwner

  if (!nextOwner) {
    summaryPositions.value = []
    summaryPositionMetricsSnapshots.value = {}
    positionMetricsSnapshots.value = {}
    positionsStore.clear()
    return
  }

  void kline.Kline.getPoolStats(kline.TickerInterval.OneDay)
  void refreshSummaryPositions(nextOwner)
  await positionsStore.fetchPositions(nextOwner, selectedStatus.value)
  void refreshPositionMetricsSnapshots(nextOwner, selectedStatus.value)
}

const schedulePositionsRefresh = () => {
  if (positionsRefreshTimer.value !== undefined) {
    window.clearTimeout(positionsRefreshTimer.value)
  }
  positionsRefreshTimer.value = window.setTimeout(() => {
    positionsRefreshTimer.value = undefined
    void refreshPositions()
  }, 250)
}

const positionsInvalidationMatchesOwner = (payload: PositionsInvalidationPayload) => {
  if (!owner.value) return false
  return (payload.events || []).some((event) => {
    const owners = event.owners || []
    return owners.length === 0 || owners.includes(owner.value)
  })
}

const positionStatusLabel = (status: Position['status']) => {
  if (status === 'active') return 'Active'
  if (status === 'virtual') return 'Virtual'
  return 'Closed'
}
const tokenApplication = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return undefined
  return ams.Ams.application(token)
}
const tokenTicker = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_TICKER
  const application = tokenApplication(token)
  const memeSpec = JSON.parse(application?.spec || '{}') as meme.Meme
  return memeSpec?.ticker || token
}
const tokenLogo = (token: string) => {
  if (!token || token === constants.LINERA_NATIVE_ID) return constants.LINERA_LOGO
  const application = tokenApplication(token)
  return application ? ams.Ams.applicationLogo(application) : constants.LINERA_LOGO
}
const positionMetrics = (position: Position) => positionMetricsFor(position, positionMetricsSnapshots.value)
const summaryPositionMetrics = (position: Position) => positionMetricsFor(position, summaryPositionMetricsSnapshots.value)
const summaryVirtualPositionMetrics = (position: Pick<Position, 'pool_application' | 'pool_id'>) => (
  virtualPositionMetricsFor(position, summaryPositionMetricsSnapshots.value)
)
const rewardPositions = computed(() => selectRewardPositions(summaryPositions.value, owner.value))
const positionRewardLiquidity = (position: Position) => positionDisplayLiquidityAmounts(
  position,
  summaryPositionMetrics(position),
  summaryVirtualPositionMetrics(position),
).liquidity
const formattedLiquidityShare = computed(() => {
  const total = rewardPositions.value.reduce((sum, position) => (
    sum + Number.parseFloat(positionRewardLiquidity(position))
  ), 0)
  return formatFixedLiquidity(Number.isFinite(total) ? total : 0, 2)
})
const nativeValuationTotal = (
  positions: Position[],
  selectAmounts: (position: Position) => Array<{ token: string, amount: string | null | undefined }>,
) => {
  let memeValueNative = 0
  let nativeAmount = 0
  positions.forEach((position) => {
    selectAmounts(position).forEach(({ token, amount }) => {
      const numeric = Number.parseFloat(amount || '0')
      if (!Number.isFinite(numeric)) return
      if (token === constants.LINERA_NATIVE_ID) {
        nativeAmount += numeric
        return
      }
      memeValueNative += numeric * (nativePriceMap.value.get(token) || 0)
    })
  })

  return nativeAmount + memeValueNative
}
const nativeYieldLabel = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return `0 ${constants.LINERA_TICKER}`
  return `≈ ${formatLiquidity(value)} ${constants.LINERA_TICKER}`
}
const currentValue = computed(() => nativeValuationTotal(
  rewardPositions.value.filter((position) => position.status !== 'closed'),
  (position) => {
    const metrics = summaryPositionMetrics(position)
    const virtualMetrics = summaryVirtualPositionMetrics(position)
    return [
      { token: position.token_0, amount: sumAmount(metrics?.redeemable_amount0, virtualMetrics?.protocol_fee_amount0) },
      { token: position.token_1, amount: sumAmount(metrics?.redeemable_amount1, virtualMetrics?.protocol_fee_amount1) },
    ]
  },
))
const currentValueSummary = computed(() => ({
  label: nativeYieldLabel(currentValue.value),
}))
const virtualBootstrapFor = (position: Position) => allPositions.value.find((candidate) => (
  isVirtualPosition(candidate) &&
  candidate.pool_application === position.pool_application &&
  Number(candidate.pool_id) === Number(position.pool_id) &&
  candidate.protocol_fee_receiver_account === owner.value
))
const summaryVirtualBootstrapFor = (position: Position) => summaryPositions.value.find((candidate) => (
  isVirtualPosition(candidate) &&
  candidate.pool_application === position.pool_application &&
  Number(candidate.pool_id) === Number(position.pool_id) &&
  candidate.protocol_fee_receiver_account === owner.value
))
const virtualBootstrapDisplayFor = (position: Position) => (
  position.status === 'active'
    ? virtualBootstrapFor(position) || summaryVirtualBootstrapFor(position) || (positionHasVirtualReference(position, owner.value) ? position : undefined)
    : undefined
)
const tokenAmountFor = (position: Position, token: string, amount0: string | null | undefined, amount1: string | null | undefined) => (
  token === position.token_0 ? amount0 : amount1
)
const sumAmount = (...values: Array<string | null | undefined>) => {
  const total = values.reduce((sum, value) => {
    const numeric = Number.parseFloat(value || '0')
    return Number.isFinite(numeric) ? sum + numeric : sum
  }, 0)
  return Number.isFinite(total) ? String(total) : '0'
}
const positionVirtualMetrics = (position: Position) => (
  virtualBootstrapDisplayFor(position) ? summaryVirtualPositionMetrics(position) : undefined
)
const positionDisplayLiquidity = (position: Position) => positionDisplayLiquidityAmounts(
  position,
  positionMetrics(position),
  positionVirtualMetrics(position),
)
const pooledTokenLabel = (position: Position, token: string) => {
  const liquidity = positionDisplayLiquidity(position)
  const amount = tokenAmountFor(position, token, liquidity.amount0, liquidity.amount1)
  return `${formatLiquidity(amount || '0')} ${tokenTicker(token)}`
}
const pooledTokenIncludesVirtual = (position: Position, token: string) => (
  token === constants.LINERA_NATIVE_ID &&
  Number.parseFloat(tokenAmountFor(
    position,
    token,
    positionVirtualMetrics(position)?.protocol_fee_amount0,
    positionVirtualMetrics(position)?.protocol_fee_amount1,
  ) || '0') > 0
)
const positionShareRatio = (position: Position) => {
  const ratio = positionDisplayShareRatio(position, positionMetrics(position), positionVirtualMetrics(position))

  if (!Number.isFinite(ratio) || ratio <= 0) return 0
  return ratio
}
const positionPoolShareLabel = (position: Position) => {
  const ratio = positionShareRatio(position)
  if (ratio <= 0) return '0%'
  return `${(ratio * 100).toFixed(ratio >= 0.01 ? 2 : 4).replace(/\.?0+$/, '')}%`
}
const formatPercentLabel = (value: number, fractionDigits = 2) => {
  if (!Number.isFinite(value) || value <= 0) return '0%'
  return `${value.toFixed(fractionDigits).replace(/\.?0+$/, '')}%`
}
const positionFeesLabel = (position: Position) => {
  const metrics = positionMetrics(position)
  const virtualMetrics = positionVirtualMetrics(position)
  if (!metrics && !virtualMetrics) {
    return {
      token0: '--',
      token1: '--',
    }
  }

  return {
    token0: `${formatLiquidity(sumAmount(metrics?.fee_amount0, virtualMetrics?.protocol_fee_amount0))} ${tokenTicker(position.token_0)}`,
    token1: `${formatLiquidity(sumAmount(metrics?.fee_amount1, virtualMetrics?.protocol_fee_amount1))} ${tokenTicker(position.token_1)}`,
  }
}
const hasMetricsWarning = (position: Position) => {
  const metrics = positionMetrics(position)
  return Boolean(metrics?.value_warning_message || (metrics?.value_warning_codes?.length || 0) > 0)
}
const metricsWarningMessage = (position: Position) => {
  const metrics = positionMetrics(position)
  if (!metrics) return 'Actual LP metrics are still updating.'
  if (metrics.value_warning_message) return metrics.value_warning_message
  return 'Current fee values are still updating.'
}
const positionAprLabel = (position: Position) => {
  const metrics = positionMetrics(position)
  const virtualMetrics = positionVirtualMetrics(position)
  if (!metrics && !virtualMetrics) return '--'

  const feeNative = nativeValuationTotal([position], () => [
    { token: position.token_0, amount: sumAmount(metrics?.trailing_24h_fee_amount0, virtualMetrics?.trailing_24h_fee_amount0) },
    { token: position.token_1, amount: sumAmount(metrics?.trailing_24h_fee_amount1, virtualMetrics?.trailing_24h_fee_amount1) },
  ])
  const positionValue = nativeValuationTotal([position], () => [
    { token: position.token_0, amount: sumAmount(metrics?.redeemable_amount0, virtualMetrics?.protocol_fee_amount0) },
    { token: position.token_1, amount: sumAmount(metrics?.redeemable_amount1, virtualMetrics?.protocol_fee_amount1) },
  ])
  if (!Number.isFinite(feeNative) || !Number.isFinite(positionValue) || positionValue <= 0) return '--'

  return formatPercentLabel((feeNative / positionValue) * 365 * 100, 4)
}
const refreshSummaryPositions = async (nextOwner: string) => {
  const requestSerial = ++summaryPositionsRequestSerial.value

  if (!walletConnected.value || !nextOwner) {
    summaryPositions.value = []
    return
  }

  const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/positions`)
  const response = await axios.get<PositionsResponse>(url, {
    params: { owner: nextOwner, status: 'all' },
  })
  const metricsResponse = await kline.Kline.getPositionMetrics(nextOwner, 'all')

  if (requestSerial !== summaryPositionsRequestSerial.value) return
  summaryPositions.value = response.data.positions
  summaryPositionMetricsSnapshots.value = Object.fromEntries(
    (metricsResponse?.metrics || []).map((entry) => [
      positionMetricsKey(entry),
      entry,
    ]),
  )
}
const actionMetrics = (position: Position) => (
  positionMetrics(position) || summaryPositionMetrics(position) || positionVirtualMetrics(position)
)
const positionActionLabel = (position: Position) => (
  resolvePositionActionLabel(position, actionMetrics(position), owner.value, allPositions.value)
)
const canUsePositionAction = (position: Position) => (
  resolveCanUsePositionAction(position, actionMetrics(position), owner.value, allPositions.value)
)
const formatLiquidity = (value: string | number) => {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  if (!Number.isFinite(numeric)) return '0'
  if (numeric === 0) return '0'
  if (numeric >= 1000) {
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 2,
      minimumFractionDigits: 0,
    }).format(numeric)
  }
  if (numeric >= 1) return numeric.toFixed(4).replace(/\.?0+$/, '')
  return numeric.toFixed(6).replace(/\.?0+$/, '')
}
const formatFixedLiquidity = (value: string | number, fractionDigits: number) => {
  const numeric = typeof value === 'number' ? value : Number.parseFloat(value || '0')
  if (!Number.isFinite(numeric)) return (0).toFixed(fractionDigits)
  return numeric.toFixed(fractionDigits)
}
const onExplorePoolsClick = () => {
  void router.push('/explore')
}
const onNewPositionClick = () => {
  void router.push('/pools/add-liquidity')
}
const onManagePositionClick = (position: Position) => {
  const context = {
    mode: Number.parseFloat(position.current_liquidity || '0') > 0 ? 'liquidity' as const : 'fees' as const,
  }
  void router.push(buildRemoveLiquidityRoute({
    token0: position.token_0,
    token1: position.token_1,
  }, context))
}

const refreshPositionMetricsSnapshots = async (
  nextOwner: string,
  status: PositionStatusFilter,
) => {
  const requestSerial = ++positionMetricsRequestSerial.value

  if (!walletConnected.value || !positionsStore.positions.length || !nextOwner) {
    positionMetricsSnapshots.value = {}
    return
  }

  const response = await kline.Kline.getPositionMetrics(nextOwner, status)
  if (requestSerial !== positionMetricsRequestSerial.value) return

  const metrics = response?.metrics || []
  positionMetricsSnapshots.value = Object.fromEntries(
    metrics.map((entry) => [
      positionMetricsKey(entry),
      entry,
    ]),
  )
}

watch(
  [
    selectedStatus,
    () => userStore.chainId,
    () => userStore.publicKey,
    () => userStore.walletType,
    () => pools.value.length,
  ],
  () => {
    void refreshPositions()
  },
  { immediate: true },
)

watch(
  owner,
  (nextOwner) => {
    if (!nextOwner) return
    kline.Kline.initialize()
    kline.Kline.subscribePositions(nextOwner)
  },
  { immediate: true },
)

const unsubscribePositionsListener = kline.Kline.onPositions((payload) => {
  if (!positionsInvalidationMatchesOwner(payload)) return
  schedulePositionsRefresh()
})

onMounted(() => {
  swap.Swap.getPools()
})

onBeforeUnmount(() => {
  unsubscribePositionsListener?.()
  if (positionsRefreshTimer.value !== undefined) {
    window.clearTimeout(positionsRefreshTimer.value)
  }
})

useMeta(() => ({
  script: {
    positionsStructuredData: {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'MicroMeme Positions',
        description: 'Positions view for liquidity positions on MicroMeme.',
      }),
    },
  },
}))

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Positions | MicroMeme',
  description:
    route.meta.seo?.description ||
    'Review your liquidity positions and pool share on MicroMeme.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'MicroMeme positions',
    'Liquidity positions',
    'Liquidity share',
  ],
}))
</script>

<style scoped lang='sass'>
.positions-page
  padding-top: 28px
  padding-bottom: 72px

.main-column
  width: 100%
  max-width: 760px
  margin: 0 auto

.reward-card,
.empty-card,
.notice-row,
.position-card
  border: 1px solid rgba(255, 255, 255, 0.08)
  background: rgba(255, 255, 255, 0.018)
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025)

.reward-card
  position: relative
  overflow: hidden
  display: block
  padding: 24px
  border-radius: 28px
  background: radial-gradient(circle at 12% 0%, rgba(247, 196, 92, 0.16), transparent 34%), radial-gradient(circle at 96% 18%, rgba(112, 221, 166, 0.10), transparent 34%), linear-gradient(135deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.014))

  &::after
    content: ''
    position: absolute
    inset: 1px
    border-radius: 27px
    pointer-events: none
    background-image: radial-gradient(rgba(255, 255, 255, 0.05) 0.7px, transparent 0.7px)
    background-size: 12px 12px
    background-position: -5px -5px
    opacity: 0.8

.reward-hero,
.reward-yield-strip
  position: relative
  z-index: 1

.reward-kicker
  margin-bottom: 12px
  color: #9aa0ab
  font-size: 12px
  font-weight: 800
  letter-spacing: 0.12em
  text-transform: uppercase

.reward-copy
  min-width: 0

.reward-value-row
  display: flex
  align-items: baseline
  justify-content: space-between
  gap: 18px
  min-width: 0

.reward-value
  display: flex
  align-items: baseline
  gap: 10px
  flex-wrap: nowrap
  min-width: 0
  font-size: clamp(44px, 8vw, 68px)
  line-height: 1
  letter-spacing: -0.06em
  font-weight: 650
  color: var(--q-light)

.reward-value span
  white-space: nowrap

.reward-unit
  display: inline-flex
  align-items: center
  height: 0.38em
  font-size: 0.34em
  line-height: 1
  letter-spacing: 0.02em
  color: #f3cf7a
  font-weight: 800

.reward-inline-logo
  display: inline-block
  width: 0.38em !important
  height: 0.38em !important
  flex: 0 0 auto
  transform: translateY(0.08em)

.reward-native-value
  display: inline-flex
  align-items: center
  justify-content: flex-end
  gap: 7px
  flex: 0 0 auto
  color: #d7dde7
  font-size: clamp(15px, 2.2vw, 20px)
  font-weight: 800
  line-height: 1
  letter-spacing: -0.02em
  text-align: right
  white-space: nowrap

.reward-native-logo
  width: 1em !important
  height: 1em !important
  flex: 0 0 auto

.reward-label
  margin-top: 10px
  font-size: 14px
  font-weight: 600
  color: #9aa0ab

.reward-yield-strip
  display: flex
  align-items: stretch
  justify-content: space-between
  gap: 10px
  width: 100%
  margin-top: 24px
  border: 1px solid rgba(255, 255, 255, 0.07)
  border-radius: 20px
  background: rgba(10, 12, 18, 0.34)
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035)

.reward-yield-item
  display: grid
  gap: 6px
  min-width: 0
  flex: 1 1 0
  padding: 12px 14px
  border-radius: 0
  background: rgba(255, 255, 255, 0.035)
  flex: 1 1 0
  text-align: left

  &:first-child
    border-radius: 19px 0 0 19px

  &:last-child
    border-radius: 0 19px 19px 0

.reward-yield-item-primary
  background: rgba(255, 255, 255, 0.055)

.reward-yield-item-protocol .reward-yield-value
  color: #f3cf7a

.reward-yield-label
  font-size: 12px
  font-weight: 700
  letter-spacing: 0.04em
  color: #9aa0ab
  text-transform: uppercase

.reward-yield-value
  color: var(--q-light)
  font-size: 17px
  font-weight: 800
  line-height: 1.1
  white-space: nowrap

.reward-info
  display: inline-flex
  align-items: center
  justify-content: center
  width: 16px
  height: 16px
  margin-left: 6px
  border-radius: 999px
  border: 1px solid rgba(255, 255, 255, 0.1)
  background: rgba(255, 255, 255, 0.04)
  color: #aab1bd
  font-size: 10px
  font-weight: 600
  vertical-align: middle
  cursor: help
  transition: background-color 160ms ease, border-color 160ms ease, color 160ms ease, transform 160ms ease

  &:hover
    background: rgba(255, 255, 255, 0.08)
    border-color: rgba(255, 255, 255, 0.18)
    color: #dbe2ec
    transform: translateY(-1px)

:global(.reward-tooltip.q-tooltip)
  max-width: 420px
  padding: 12px 14px !important
  color: #d7dde7 !important
  background: rgba(16, 18, 24, 0.96) !important
  border: 1px solid rgba(255, 255, 255, 0.1) !important
  border-radius: 14px !important
  box-shadow: none !important
  font-size: 14px
  line-height: 1.4
  white-space: normal !important
  display: block

:global(.reward-tooltip.q-tooltip p)
  margin: 0

:global(.reward-tooltip.q-tooltip p + p)
  margin-top: 5px

.positions-section
  margin-top: 34px

.positions-header
  display: flex
  align-items: center
  justify-content: space-between
  gap: 16px

.positions-title
  font-size: 22px
  line-height: 1.1
  font-weight: 700
  color: var(--q-light)

.filter-row
  display: flex
  flex-wrap: wrap
  gap: 8px

.filter-btn,
.empty-btn
  border: 0
  background: transparent
  color: inherit
  font: inherit
  cursor: pointer

.filter-btn
  position: relative
  display: inline-flex
  align-items: center
  justify-content: center
  gap: 8px
  min-height: 40px
  padding: 0 16px
  border-radius: 18px
  background: rgba(255, 255, 255, 0.06)
  color: var(--q-light)
  font-size: 14px
  font-weight: 700
  line-height: 1
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03)
  vertical-align: middle

.filter-btn-primary
  background: #f5f5f7
  color: #111

.filter-plus
  font-size: 16px
  line-height: 1

.filter-caret
  display: inline-flex
  align-items: center
  justify-content: center
  height: 1em
  font-size: 12px
  line-height: 1
  opacity: 0.75
  transform: translateY(-1px)

:global(.status-menu.q-menu)
  min-width: 176px
  padding: 6px
  border: 1px solid rgba(255, 255, 255, 0.08)
  border-radius: 16px
  background: rgba(16, 18, 24, 0.98)
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28)

:global(.status-menu-list)
  padding: 0

:global(.status-menu-item)
  min-height: 38px
  border-radius: 12px
  color: #d7dde7
  font-size: 14px
  font-weight: 600

:global(.status-menu-item:hover)
  background: rgba(255, 255, 255, 0.06)

.positions-list
  display: grid
  gap: 14px
  margin-top: 20px

.position-card
  padding: 18px 18px 16px
  border-radius: 20px

.position-card-loading
  display: grid
  gap: 12px

.position-card-header
  display: flex
  align-items: center
  justify-content: space-between
  gap: 16px

.position-pair-wrap
  display: flex
  align-items: center
  gap: 14px

.position-header-actions
  display: flex
  align-items: center
  gap: 10px

.position-pair
  font-size: 18px
  font-weight: 700
  color: var(--q-light)

.position-subtitle,
.position-share-meta,
.metric-label
  font-size: 13px
  color: #9aa0ab

.metric-warning
  display: inline-flex
  align-items: center
  justify-content: center
  width: 14px
  height: 14px
  margin-left: 6px
  border-radius: 999px
  background: rgba(247, 196, 92, 0.16)
  color: #f3cf7a
  font-size: 10px
  font-weight: 700
  line-height: 1
  cursor: help

.metric-info
  display: inline-flex
  align-items: center
  justify-content: center
  width: 14px
  height: 14px
  margin-left: 6px
  border-radius: 999px
  border: 1px solid rgba(255, 255, 255, 0.12)
  background: rgba(255, 255, 255, 0.04)
  color: #aab1bd
  font-size: 10px
  font-weight: 700
  line-height: 1
  cursor: help

.position-subtitle
  margin-top: 4px

.position-badge
  display: inline-flex
  align-items: center
  justify-content: center
  min-height: 30px
  padding: 0 12px
  border-radius: 999px
  font-size: 12px
  font-weight: 700
  line-height: 1
  text-align: center

.position-badge-active
  background: rgba(77, 214, 143, 0.12)
  color: #7de9ab

.position-badge-closed
  background: rgba(255, 255, 255, 0.08)
  color: #d1d7e0

.position-badge-virtual
  background: rgba(247, 196, 92, 0.14)
  color: #f3cf7a

.position-badge-fee-to
  background: rgba(247, 196, 92, 0.14)
  color: #f3cf7a

.position-summary-row
  margin-top: 18px
  padding-top: 16px
  border-top: 1px solid rgba(255, 255, 255, 0.06)
  display: grid
  grid-template-columns: repeat(var(--position-summary-columns, 4), minmax(0, 1fr))
  gap: 12px

.position-menu-btn
  border: 0
  border-radius: 999px
  width: 30px
  min-width: 30px
  height: 30px
  display: inline-flex
  align-items: center
  justify-content: center
  font: inherit
  font-size: 18px
  font-weight: 700
  cursor: pointer
  background: rgba(255, 255, 255, 0.06)
  color: var(--q-light)
  line-height: 1
  padding: 0

.position-metric
  display: grid
  gap: 6px
  min-width: 0

.metric-value
  font-size: 14px
  font-weight: 600
  color: var(--q-light)

.metric-value-stack
  display: grid
  gap: 2px
  white-space: normal
  word-break: break-word

.pooled-token-line
  display: inline-flex
  align-items: center
  flex-wrap: wrap
  gap: 8px

.virtual-bootstrap-tag
  display: inline-flex
  align-items: center
  min-height: 20px
  padding: 0 8px
  border-radius: 999px
  background: rgba(255, 255, 255, 0.08)
  color: #9aa0ab
  font-size: 11px
  font-weight: 700
  line-height: 1

.empty-card
  display: flex
  flex-direction: column
  align-items: center
  justify-content: center
  min-height: 198px
  margin-top: 20px
  padding: 28px 24px
  border-radius: 18px
  text-align: center

.empty-icon-wrap
  display: flex
  align-items: center
  justify-content: center
  width: 42px
  height: 42px
  border-radius: 12px
  background: rgba(255, 255, 255, 0.07)

.empty-icon
  color: #d8d8d8
  font-size: 22px
  line-height: 1

.empty-title
  margin-top: 18px
  font-size: 16px
  font-weight: 700
  color: var(--q-light)

.empty-text
  max-width: 440px
  margin-top: 10px
  font-size: 14px
  line-height: 1.55
  color: #9aa0ab

.empty-actions
  display: flex
  gap: 10px
  margin-top: 18px

.empty-btn
  min-width: 128px
  height: 36px
  padding: 0 18px
  border-radius: 14px
  font-size: 14px
  font-weight: 700

.empty-btn-secondary
  background: rgba(255, 255, 255, 0.08)
  color: var(--q-light)

.empty-btn-primary
  background: #f5f5f7
  color: #111

.notice-row
  display: flex
  align-items: flex-start
  gap: 12px
  margin-top: 18px
  padding: 14px 16px
  border-radius: 14px

.notice-icon
  display: flex
  align-items: center
  justify-content: center
  width: 18px
  height: 18px
  margin-top: 2px
  border-radius: 999px
  background: rgba(255, 255, 255, 0.08)
  font-size: 12px
  font-weight: 700
  color: var(--q-light)

.notice-copy
  min-width: 0
  flex: 1 1 auto

.notice-title
  font-size: 14px
  font-weight: 700
  color: var(--q-light)

.notice-text
  margin-top: 2px
  font-size: 13px
  color: #9aa0ab

@media (max-width: 720px)
  .positions-page
    padding-top: 18px

  .reward-card,
  .empty-card,
  .notice-row,
  .position-card
    padding-left: 16px
    padding-right: 16px

  .reward-yield-strip
    flex-wrap: wrap
    justify-content: flex-start

  .reward-yield-item
    flex: 1 1 100%
    border-radius: 0
    text-align: left

    &:first-child
      border-radius: 19px 19px 0 0

    &:last-child
      border-radius: 0 0 19px 19px

  .reward-yield-value
    white-space: normal

  .reward-value-row
    display: grid
    gap: 12px

  .reward-native-value
    margin-bottom: 0
    text-align: left

  .positions-header,
  .position-card-header
    display: block

  .filter-row,
  .position-header-actions
    margin-top: 16px

  .position-summary-row
    gap: 10px

  .metric-label
    font-size: 12px

  .metric-value
    font-size: 13px

  .empty-actions
    flex-direction: column
    width: 100%

  .empty-btn
    width: 100%
</style>
