<template>
  <q-page class='row justify-center'>
    <main class='page-width positions-page'>
      <section class='main-column'>
        <div class='reward-card'>
          <div class='reward-copy'>
            <div class='reward-value'>
              {{ formattedLiquidityShare }} LMM
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
              <div class='position-summary-row'>
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
                  <div class='position-pair-icons'>
                    <q-avatar size='30px' class='position-token-avatar position-token-avatar-front'>
                      <q-img :src='tokenLogo(position.token_0)' fit='contain' />
                    </q-avatar>
                    <q-avatar size='30px' class='position-token-avatar position-token-avatar-back'>
                      <q-img :src='tokenLogo(position.token_1)' fit='contain' />
                    </q-avatar>
                  </div>
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
                    {{ position.status === 'active' ? 'Active' : 'Closed' }}
                  </span>
                  <span
                    v-if='positionMetrics(position)?.owner_is_fee_to'
                    class='position-badge position-badge-fee-to'
                  >
                    Protocol Fee Receiver
                  </span>
                </div>
              </div>

              <div class='position-summary-row'>
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
                  <span class='metric-label'>Trading Fees</span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ positionFeesLabel(position).token0 }}</span>
                    <span>{{ positionFeesLabel(position).token1 }}</span>
                  </span>
                </div>
                <div v-if='positionMetrics(position)?.owner_is_fee_to' class='position-metric'>
                  <span class='metric-label'>Protocol Fees</span>
                  <span class='metric-value metric-value-stack'>
                    <span>{{ positionProtocolFeesLabel(position).token0 }}</span>
                    <span>{{ positionProtocolFeesLabel(position).token1 }}</span>
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
import { computed, ref, watch } from 'vue'
import { useMeta } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import { usePageSeo } from 'src/utils/seo'
import { constants } from 'src/constant'
import { buildRemoveLiquidityRoute } from 'src/components/pools/poolFlow'
import { useUserStore } from 'src/stores/user'
import { usePositionsStore, type Position, type PositionStatusFilter } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'
import { ams, kline, swap, type meme } from 'src/stores/export'
import { protocol } from 'src/utils'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const positionsStore = usePositionsStore()

const selectedStatus = ref<PositionStatusFilter>('active')
const owner = ref('')

const statusOptions: Array<{ value: PositionStatusFilter; label: string }> = [
  { value: 'all', label: 'All positions' },
  { value: 'active', label: 'Active' },
  { value: 'closed', label: 'Closed' },
]

const selectedStatusLabel = computed(() => (
  statusOptions.find((option) => option.value === selectedStatus.value)?.label || 'Status'
))
const walletConnected = computed(() => Boolean(userStore.chainId && userStore.publicKey))
const visiblePositions = computed(() => positionsStore.positions)
const formattedLiquidityShare = computed(() => formatLiquidity(positionsStore.activeLiquidityShare))
const pools = computed(() => swap.Swap.pools())
const nativePriceMap = computed(() => protocol.buildNativePriceMap(pools.value))
const positionMetricsSnapshots = ref<Record<string, PositionMetricsEntry>>({})
const positionMetricsRequestSerial = ref(0)
const showClosedHint = computed(() => (
  walletConnected.value &&
  positionsStore.loaded &&
  !positionsStore.loading &&
  !visiblePositions.value.length &&
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
  const account = await userStore.account()
  if (!account.owner || !account.chain_id) return ''
  return `${account.chain_id}:${account.owner}`
}

const refreshPositions = async () => {
  if (!walletConnected.value) {
    owner.value = ''
    positionMetricsSnapshots.value = {}
    positionsStore.clear()
    return
  }

  const nextOwner = await buildOwnerParam()
  owner.value = nextOwner

  if (!nextOwner) {
    positionMetricsSnapshots.value = {}
    positionsStore.clear()
    return
  }

  void kline.Kline.getPoolStats(kline.TickerInterval.OneDay)
  await positionsStore.fetchPositions(nextOwner, selectedStatus.value)
  void refreshPositionMetricsSnapshots(nextOwner, selectedStatus.value)
}

const positionKey = (position: Position) => `${position.pool_application}:${position.pool_id}:${position.status}`
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
const positionMetrics = (position: Position) => positionMetricsSnapshots.value[positionKey(position)]
const positionLiquidity = (position: Position) =>
  ({
    liquidity:
      positionMetrics(position)?.position_liquidity_live || position.current_liquidity || '0',
    amount0: positionMetrics(position)?.redeemable_amount0 || '0',
    amount1: positionMetrics(position)?.redeemable_amount1 || '0',
  })
const poolForPosition = (position: Position) => swap.Swap.getPool(position.token_0, position.token_1)
const positionShareRatio = (position: Position) => {
  const ratio = Number.parseFloat(positionMetrics(position)?.exact_share_ratio || '0')

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
  if (!metrics) {
    return {
      token0: '--',
      token1: '--',
    }
  }

  if (!metrics.exact_fee_supported) {
    return {
      token0: 'Unavailable',
      token1: 'Unavailable',
    }
  }

  return {
    token0: `${formatLiquidity(metrics.fee_amount0 || '0')} ${tokenTicker(position.token_0)}`,
    token1: `${formatLiquidity(metrics.fee_amount1 || '0')} ${tokenTicker(position.token_1)}`,
  }
}
const positionProtocolFeesLabel = (position: Position) => {
  const metrics = positionMetrics(position)
  if (!metrics?.owner_is_fee_to) {
    return {
      token0: '--',
      token1: '--',
    }
  }

  if (!metrics.exact_fee_supported) {
    return {
      token0: 'Unavailable',
      token1: 'Unavailable',
    }
  }

  return {
    token0: `${formatLiquidity(metrics.protocol_fee_amount0 || '0')} ${tokenTicker(position.token_0)}`,
    token1: `${formatLiquidity(metrics.protocol_fee_amount1 || '0')} ${tokenTicker(position.token_1)}`,
  }
}
const positionAprLabel = (position: Position) => {
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

  const response = await kline.Kline.getPositionMetrics(nextOwner, status)
  if (requestSerial !== positionMetricsRequestSerial.value) return

  const metrics = response?.metrics || []
  positionMetricsSnapshots.value = Object.fromEntries(
    metrics.map((entry) => [
      `${entry.pool_application}:${entry.pool_id}:${entry.status}`,
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
  font-size: 50px
  line-height: 1
  letter-spacing: -0.05em
  font-weight: 500
  color: var(--q-light)

.reward-inline-logo
  display: inline-block
  width: 0.92em !important
  height: 0.92em !important
  margin-left: 6px
  vertical-align: -0.06em

.reward-label
  margin-top: 8px
  font-size: 14px
  font-weight: 600
  color: #9aa0ab

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
  gap: 8px
  height: 38px
  padding: 0 14px
  border-radius: 18px
  background: rgba(255, 255, 255, 0.06)
  color: var(--q-light)
  font-size: 14px
  font-weight: 700
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03)

.filter-btn-primary
  background: #f5f5f7
  color: #111

.filter-plus
  font-size: 16px
  line-height: 1

.filter-caret
  font-size: 12px
  opacity: 0.75

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

.position-pair-icons
  position: relative
  width: 52px
  height: 30px

.position-token-avatar
  position: absolute
  top: 0
  border: 2px solid rgba(16, 18, 24, 0.88)
  background: rgba(255, 255, 255, 0.1)

.position-token-avatar-front
  left: 0
  z-index: 2

.position-token-avatar-back
  left: 20px

.position-pair
  font-size: 18px
  font-weight: 700
  color: var(--q-light)

.position-subtitle,
.position-share-meta,
.metric-label
  font-size: 13px
  color: #9aa0ab

.position-subtitle
  margin-top: 4px

.position-badge
  display: inline-flex
  align-items: center
  height: 28px
  padding: 0 12px
  border-radius: 999px
  font-size: 12px
  font-weight: 700

.position-badge-active
  background: rgba(77, 214, 143, 0.12)
  color: #7de9ab

.position-badge-closed
  background: rgba(255, 255, 255, 0.08)
  color: #d1d7e0

.position-badge-fee-to
  background: rgba(247, 196, 92, 0.14)
  color: #f3cf7a

.position-summary-row
  margin-top: 18px
  padding-top: 16px
  border-top: 1px solid rgba(255, 255, 255, 0.06)
  display: grid
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1.65fr) repeat(2, minmax(0, 0.8fr))
  gap: 14px 18px

.position-summary-row-fee-to
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1.5fr) repeat(3, minmax(0, 0.8fr))

.position-menu-btn
  border: 0
  border-radius: 12px
  width: 30px
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
  overflow-wrap: anywhere

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

  .positions-header,
  .position-card-header
    display: block

  .filter-row,
  .position-header-actions
    margin-top: 16px

  .position-summary-row
    grid-template-columns: repeat(2, minmax(0, 1fr))

  .empty-actions
    flex-direction: column
    width: 100%

  .empty-btn
    width: 100%
</style>
