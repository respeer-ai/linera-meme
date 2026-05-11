<template>
  <q-page class='row justify-center'>
    <main class='page-width positions-page'>
      <section class='main-column'>
        <div class='reward-card'>
          <div class='reward-copy'>
            <div class='reward-value'>
              <span>{{ formattedLiquidityShare }} LMM</span>
              <q-img class='reward-inline-logo' :src='constants.MICROMEME_LOGO' width='18px' height='18px' fit='contain' />
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
          <div v-if='walletConnected' class='reward-fee-split'>
            <div class='reward-fee-group'>
              <span class='reward-fee-label'>Trading yield</span>
              <span class='reward-fee-values'>
                <span v-for='item in tradingFeeSummary' :key='`trading-${item.key}`'>{{ item.label }}</span>
              </span>
            </div>
            <span v-if='hasProtocolFeeReceiverPosition' class='reward-fee-divider'>|</span>
            <div v-if='hasProtocolFeeReceiverPosition' class='reward-fee-group'>
              <span class='reward-fee-label'>Protocol yield</span>
              <span class='reward-fee-values reward-fee-values-protocol'>
                <span v-for='item in protocolFeeSummary' :key='`protocol-${item.key}`'>{{ item.label }}</span>
              </span>
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
                  <button class='position-menu-btn' aria-label='Position actions'>
                    ⋮
                    <q-menu class='status-menu position-actions-menu' anchor='bottom right' self='top right' :offset='[0, 10]'>
                      <q-list dense class='status-menu-list'>
                        <q-item
                          clickable
                          v-close-popup
                          class='status-menu-item'
                          :disable='position.status !== "active" || !hasLiquidity(position)'
                          @click='onManagePositionClick(position)'
                        >
                          <q-item-section>Remove</q-item-section>
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
                v-if='isVirtualPosition(position)'
                class='position-summary-row position-summary-row-virtual'
                :style='{ "--position-summary-columns": "2" }'
              >
                <div class='position-metric'>
                  <span class='metric-label'>Deposited token</span>
                  <span class='metric-value metric-value-stack virtual-bootstrap-stack'>
                    <span class='virtual-bootstrap-line'>
                      <span>{{ virtualDepositedLiquidityItem(position).label }}</span>
                      <span class='virtual-bootstrap-tag'>Deposited</span>
                    </span>
                  </span>
                </div>
                <div class='position-metric position-metric-virtual-quote'>
                  <span class='metric-label'>
                    Virtual reference
                    <span class='metric-info'>?
                      <q-tooltip class='reward-tooltip' anchor='top middle' self='bottom middle'>
                        Used to seed the initial pool price; not deposited as liquidity.
                      </q-tooltip>
                    </span>
                  </span>
                  <span class='metric-value metric-value-stack virtual-bootstrap-stack'>
                    <span class='virtual-bootstrap-line virtual-bootstrap-line-quote'>
                      <span>{{ virtualQuoteLiquidityItem(position).label }}</span>
                      <span class='virtual-bootstrap-tag'>Virtual</span>
                    </span>
                  </span>
                </div>
              </div>

              <div
                v-else
                class='position-summary-row'
                :style='{ "--position-summary-columns": "4" }'
              >
                <div class='position-metric'>
                  <span class='metric-label'>Pool share</span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ positionPoolShareLabel(position) }}</span>
                    <span>{{ formatLiquidity(position.current_liquidity) }} LMM</span>
                  </span>
                </div>
                <div class='position-metric'>
                  <span class='metric-label'>Pooled tokens</span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ formatLiquidity(positionLiquidity(position).amount0) }} {{ tokenTicker(position.token_0) }}</span>
                    <span>{{ formatLiquidity(positionLiquidity(position).amount1) }} {{ tokenTicker(position.token_1) }}</span>
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
import { computed, ref, watch } from 'vue'
import { useMeta } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { usePageSeo } from 'src/utils/seo'
import { constants } from 'src/constant'
import { buildRemoveLiquidityRoute } from 'src/components/pools/poolFlow'
import { useUserStore } from 'src/stores/user'
import { usePositionsStore, type Position, type PositionStatusFilter, type PositionsResponse } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'
import { account, ams, kline, swap, type meme } from 'src/stores/export'
import { protocol } from 'src/utils'
import PoolPairLogo from 'src/components/pools/PoolPairLogo.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const positionsStore = usePositionsStore()

const selectedStatus = ref<PositionStatusFilter>('active')
const owner = ref('')
const summaryPositions = ref<Position[]>([])
const summaryPositionsRequestSerial = ref(0)
const summaryPositionMetricsSnapshots = ref<Record<string, PositionMetricsEntry>>({})

const statusOptions: Array<{ value: PositionStatusFilter; label: string }> = [
  { value: 'all', label: 'All positions' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
  { value: 'virtual', label: 'Virtual' },
]

const selectedStatusLabel = computed(() => (
  statusOptions.find((option) => option.value === selectedStatus.value)?.label || 'Status'
))
const walletConnected = computed(() => Boolean(userStore.chainId && userStore.publicKey))
const allPositions = computed(() => positionsStore.positions)
const visiblePositions = computed(() => allPositions.value)
const rewardPositions = computed(() => summaryPositions.value)
const formattedLiquidityShare = computed(() => {
  const total = rewardPositions.value.reduce((sum, position) => {
    if (position.status === 'closed') return sum
    const metrics = summaryPositionMetrics(position)
    return sum + Number.parseFloat(metrics?.position_liquidity_live || position.current_liquidity || '0')
  }, 0)
  return formatFixedLiquidity(Number.isFinite(total) ? total : 0, 2)
})
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
  if (selectedStatus.value === 'virtual') return 'No virtual positions'
  return 'No positions'
})
const emptyStateText = computed(() => {
  if (!walletConnected.value) {
    return 'Connect your wallet to load liquidity positions associated with your account.'
  }
  if (selectedStatus.value === 'closed') {
    return 'You have not fully redeemed any liquidity positions yet.'
  }
  if (selectedStatus.value === 'virtual') {
    return 'No virtual initial liquidity positions are associated with your account.'
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

const positionKey = (position: Position) =>
  `${position.pool_application}:${position.pool_id}:${position.status}:${position.position_kind || 'recorded'}`
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
const positionMetrics = (position: Position) =>
  positionMetricsSnapshots.value[positionKey(position)] ||
  positionMetricsSnapshots.value[`${position.pool_application}:${position.pool_id}:${position.status}:recorded`]
const summaryPositionMetrics = (position: Position) =>
  summaryPositionMetricsSnapshots.value[positionKey(position)] ||
  summaryPositionMetricsSnapshots.value[`${position.pool_application}:${position.pool_id}:${position.status}:recorded`]
const isProtocolFeeReceiver = (position: Position) =>
  Boolean(owner.value && position.protocol_fee_receiver_account === owner.value)
const hasProtocolFeeReceiverPosition = computed(() => (
  rewardPositions.value.some((position) => isProtocolFeeReceiver(position))
))
const nativeValuation = (
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

  return [
    { key: 'meme-value', label: `Meme value ≈ ${formatLiquidity(memeValueNative)} ${constants.LINERA_TICKER}` },
    { key: 'native', label: `Native ${formatLiquidity(nativeAmount)} ${constants.LINERA_TICKER}` },
  ]
}
const isVirtualPosition = (position: Position) => position.status === 'virtual' || Boolean(position.is_virtual_position)
const virtualInitialTokenAmounts = (position: Position): Array<{ token: string, amount: string | null | undefined }> => [
  { token: position.token_0, amount: position.virtual_initial_amount0 },
  { token: position.token_1, amount: position.virtual_initial_amount1 },
]
const virtualDepositedLiquidityItem = (position: Position) => {
  const item = virtualInitialTokenAmounts(position).find(({ token, amount }) => {
    const numeric = Number.parseFloat(amount || '0')
    return token !== constants.LINERA_NATIVE_ID && Number.isFinite(numeric) && numeric > 0
  })

  if (!item) return { token: 'none', label: 'No meme token amount recorded' }
  return {
    token: item.token,
    label: `${formatLiquidity(item.amount || '0')} ${tokenTicker(item.token)}`,
  }
}
const virtualQuoteLiquidityItem = (position: Position) => {
  const item = virtualInitialTokenAmounts(position).find(({ token, amount }) => {
    const numeric = Number.parseFloat(amount || '0')
    return token === constants.LINERA_NATIVE_ID && Number.isFinite(numeric) && numeric > 0
  })

  if (!item) return { token: constants.LINERA_NATIVE_ID, label: `No ${constants.LINERA_TICKER} reference recorded` }
  return {
    token: item.token,
    label: `${formatLiquidity(item.amount || '0')} ${tokenTicker(item.token)}`,
  }
}
const positionLiquidity = (position: Position) => {
  if (isVirtualPosition(position)) {
    return {
      liquidity: position.current_liquidity || '0',
      amount0: position.virtual_initial_amount0 || '0',
      amount1: position.virtual_initial_amount1 || '0',
    }
  }

  return {
    liquidity:
      positionMetrics(position)?.position_liquidity_live || position.current_liquidity || '0',
    amount0:
      positionMetrics(position)?.redeemable_amount0 ||
      position.virtual_initial_amount0 ||
      '0',
    amount1:
      positionMetrics(position)?.redeemable_amount1 ||
      position.virtual_initial_amount1 ||
      '0',
  }
}
const poolForPosition = (position: Position) => swap.Swap.getPool(position.token_0, position.token_1)
const positionShareRatio = (position: Position) => {
  const ratio = Number.parseFloat(positionMetrics(position)?.share_ratio || '0')

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
  if (isVirtualPosition(position)) {
    return {
      token0: '--',
      token1: '--',
    }
  }

  const metrics = positionMetrics(position)
  if (!metrics) {
    return {
      token0: '--',
      token1: '--',
    }
  }

  return {
    token0: `${formatLiquidity(metrics.fee_amount0 || '0')} ${tokenTicker(position.token_0)}`,
    token1: `${formatLiquidity(metrics.fee_amount1 || '0')} ${tokenTicker(position.token_1)}`,
  }
}
const yieldSummaryPositions = computed(() => (
  hasProtocolFeeReceiverPosition.value
    ? rewardPositions.value.filter((position) => isProtocolFeeReceiver(position))
    : rewardPositions.value.filter((position) => !position.is_virtual_position)
))
const tradingFeeSummary = computed(() => nativeValuation(
  yieldSummaryPositions.value,
  (position) => {
    const metrics = summaryPositionMetrics(position)
    return [
      { token: position.token_0, amount: metrics?.fee_amount0 || '0' },
      { token: position.token_1, amount: metrics?.fee_amount1 || '0' },
    ]
  },
))
const protocolFeeSummary = computed(() => nativeValuation(
  rewardPositions.value.filter((position) => isProtocolFeeReceiver(position)),
  (position) => {
    const metrics = summaryPositionMetrics(position)
    return [
      {
        token: position.token_0,
        amount: metrics?.protocol_fee_amount0 || position.protocol_fee_reference_amount0 || '0',
      },
      {
        token: position.token_1,
        amount: metrics?.protocol_fee_amount1 || position.protocol_fee_reference_amount1 || '0',
      },
    ]
  },
))
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
      `${entry.pool_application}:${entry.pool_id}:${entry.status}:recorded`,
      entry,
    ]),
  )
}
const hasMetricsWarning = (position: Position) => {
  if (isVirtualPosition(position)) return false
  const metrics = positionMetrics(position)
  return Boolean(metrics?.value_warning_message || (metrics?.value_warning_codes?.length || 0) > 0)
}
const metricsWarningMessage = (position: Position) => {
  const metrics = positionMetrics(position)
  if (!metrics) return 'Fee values are still updating.'
  if (metrics.value_warning_message) return metrics.value_warning_message
  return 'Current fee values are still updating.'
}
const positionAprLabel = (position: Position) => {
  if (isVirtualPosition(position)) return '--'
  const selectedPool = poolForPosition(position)
  if (!selectedPool) return '--'

  const tvl = protocol.calculatePoolTvlInNative(selectedPool, nativePriceMap.value)
  const oneDayVolume = protocol.calculatePoolVolumeInNative(
    kline.Kline.poolStat(selectedPool.poolId, kline.TickerInterval.OneDay),
    nativePriceMap.value,
  )
  if (tvl === undefined || oneDayVolume === undefined) return '--'

  return formatPercentLabel(protocol.calculatePoolAprFromDailyVolume(oneDayVolume, tvl) * 100, 4)
}
const hasLiquidity = (position: Position) =>
  Number.parseFloat(positionLiquidity(position).liquidity || position.current_liquidity || '0') > 0
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
  void router.push(buildRemoveLiquidityRoute({
    token0: position.token_0,
    token1: position.token_1,
  }))
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

  const metricsStatus = status === 'virtual' ? 'all' : status
  const response = await kline.Kline.getPositionMetrics(nextOwner, metricsStatus)
  if (requestSerial !== positionMetricsRequestSerial.value) return

  const metrics = response?.metrics || []
  positionMetricsSnapshots.value = Object.fromEntries(
    metrics.map((entry) => [
      `${entry.pool_application}:${entry.pool_id}:${entry.status}:recorded`,
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

useMeta(() => ({
  script: {
    positionsStructuredData: {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'MicroMeme Positions',
        description: 'Positions view for liquidity positions and fee accrual on MicroMeme.',
      }),
    },
  },
}))

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Positions | MicroMeme',
  description:
    route.meta.seo?.description ||
    'Review your liquidity positions, pool share, and trading fee accrual on MicroMeme.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'MicroMeme positions',
    'Liquidity positions',
    'Trading fees',
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
  display: flex
  justify-content: space-between
  align-items: flex-start
  gap: 24px
  padding: 20px
  border-radius: 24px
  background-image: radial-gradient(rgba(255, 255, 255, 0.05) 0.7px, transparent 0.7px)
  background-size: 12px 12px
  background-position: -5px -5px

.reward-copy
  min-width: 0

.reward-value
  display: inline-flex
  align-items: center
  gap: 8px
  flex-wrap: nowrap
  font-size: 50px
  line-height: 1
  letter-spacing: -0.05em
  font-weight: 500
  color: var(--q-light)

.reward-inline-logo
  display: inline-block
  width: 0.92em !important
  height: 0.92em !important
  flex: 0 0 auto

.reward-label
  margin-top: 8px
  font-size: 14px
  font-weight: 600
  color: #9aa0ab

.reward-fee-split
  display: flex
  align-items: center
  justify-content: flex-end
  gap: 14px
  min-width: min(390px, 46%)
  flex: 0 0 auto
  color: #9aa0ab

.reward-fee-group
  display: grid
  gap: 5px
  min-width: 0
  text-align: right

.reward-fee-divider
  color: rgba(255, 255, 255, 0.18)
  font-size: 30px
  font-weight: 200
  line-height: 1

.reward-fee-label
  font-size: 12px
  font-weight: 700
  letter-spacing: 0.02em
  color: #9aa0ab

.reward-fee-values
  display: flex
  flex-direction: column
  gap: 2px
  color: var(--q-light)
  font-size: 14px
  font-weight: 700
  line-height: 1.25
  word-break: break-word

.reward-fee-values-protocol
  color: #f3cf7a

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

.virtual-bootstrap-stack
  gap: 8px

.virtual-bootstrap-line
  display: flex
  align-items: center
  flex-wrap: wrap
  gap: 8px

.virtual-bootstrap-line-quote
  color: #d1d7e0

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

.virtual-bootstrap-line:not(.virtual-bootstrap-line-quote) .virtual-bootstrap-tag
  background: rgba(77, 214, 143, 0.12)
  color: #7de9ab

.virtual-bootstrap-line-quote .virtual-bootstrap-tag
  background: rgba(247, 196, 92, 0.14)
  color: #f3cf7a

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

  .reward-card
    display: block

  .reward-fee-split
    justify-content: flex-start
    min-width: 0
    margin-top: 18px

  .reward-fee-group
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
