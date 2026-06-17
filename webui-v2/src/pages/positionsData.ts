import { type Position } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'

export type PositionMetricsSnapshots = Record<string, PositionMetricsEntry>
export interface PositionLiquidityDisplayAmounts {
  liquidity: string
  amount0: string
  amount1: string
}

type PositionIdentity = Pick<Position, 'pool_application' | 'pool_id' | 'status' | 'position_kind'>
type MetricsIdentity = Pick<PositionMetricsEntry, 'pool_application' | 'pool_id' | 'status'>

export const isVirtualPosition = (
  position: Pick<Position, 'status' | 'is_virtual_position'>,
) => position.status === 'virtual' || Boolean(position.is_virtual_position)

export const isPositionProtocolFeeReceiver = (
  position: Pick<Position, 'protocol_fee_receiver_account'>,
  owner: string,
) => Boolean(owner && position.protocol_fee_receiver_account === owner)

export const positionKey = (position: PositionIdentity) =>
  `${position.pool_application}:${position.pool_id}:${position.status}:${position.position_kind || 'recorded'}`

export const positionMetricsKey = (entry: MetricsIdentity) => {
  const positionKind = entry.status === 'virtual'
    ? 'virtual_initial_liquidity'
    : 'recorded'
  return `${entry.pool_application}:${entry.pool_id}:${entry.status}:${positionKind}`
}

export const positionMetricsFor = (
  position: PositionIdentity,
  snapshots: PositionMetricsSnapshots,
) => (
  snapshots[positionKey(position)] ||
  snapshots[`${position.pool_application}:${position.pool_id}:${position.status}:recorded`]
)

export const virtualPositionMetricsFor = (
  position: Pick<Position, 'pool_application' | 'pool_id'>,
  snapshots: PositionMetricsSnapshots,
) => snapshots[`${position.pool_application}:${position.pool_id}:virtual:virtual_initial_liquidity`]

export const selectDisplayPositions = (positions: Position[]) => (
  positions.filter((position) => position.status === 'active' || !isVirtualPosition(position))
)

export const selectRewardPositions = (positions: Position[], owner: string) => (
  positions.filter((position) => (
    position.status !== 'closed' &&
    (!isVirtualPosition(position) || isPositionProtocolFeeReceiver(position, owner))
  ))
)

export const positionRewardLiquidity = (
  position: Position,
  metrics: PositionMetricsEntry | undefined,
  owner: string,
) => {
  if (isVirtualPosition(position)) {
    return isPositionProtocolFeeReceiver(position, owner) ? metrics?.position_liquidity || '0' : '0'
  }
  return metrics?.position_liquidity || position.current_liquidity || '0'
}

export const positionRewardShareRatio = (
  actualMetrics: PositionMetricsEntry | undefined,
  virtualMetrics: PositionMetricsEntry | undefined,
) => {
  const total = [actualMetrics?.share_ratio, virtualMetrics?.share_ratio].reduce((sum, value) => {
    const numeric = Number.parseFloat(value || '0')
    return Number.isFinite(numeric) ? sum + numeric : sum
  }, 0)
  return Number.isFinite(total) ? total : 0
}

const numericAmount = (value: string | number | null | undefined) => {
  const numeric = Number.parseFloat(String(value || '0'))
  return Number.isFinite(numeric) ? numeric : 0
}

const amountString = (value: number) => (
  Number.isFinite(value) && value > 0 ? String(value) : '0'
)

export const virtualInitialLiquidity = (position: Position): string => (
  positiveAmount(position.virtual_current_liquidity) ? String(position.virtual_current_liquidity) : '0'
)

export const virtualInitialTokenAmount = (
  virtualLiquidity: string,
  protocolLiquidity: string | null | undefined,
  protocolTokenAmount: string | null | undefined,
  recordedInitialAmount: string | null | undefined,
) => {
  const virtualLiquidityValue = numericAmount(virtualLiquidity)
  const protocolLiquidityValue = numericAmount(protocolLiquidity)
  const protocolTokenValue = numericAmount(protocolTokenAmount)

  if (virtualLiquidityValue > 0 && protocolLiquidityValue > 0 && protocolTokenValue > 0) {
    return amountString(protocolTokenValue * virtualLiquidityValue / protocolLiquidityValue)
  }
  return positiveAmount(recordedInitialAmount) ? String(recordedInitialAmount) : '0'
}

export const positionDisplayLiquidityAmounts = (
  position: Position,
  actualMetrics: PositionMetricsEntry | undefined,
  virtualMetrics: PositionMetricsEntry | undefined,
): PositionLiquidityDisplayAmounts => {
  const actual = positionLiquidityAmounts(position, actualMetrics)
  const virtualLiquidity = virtualInitialLiquidity(position)
  const virtualInitialAmount0 = virtualInitialTokenAmount(
    virtualLiquidity,
    virtualMetrics?.position_liquidity,
    virtualMetrics?.protocol_fee_amount0,
    position.virtual_initial_amount0,
  )
  const virtualInitialAmount1 = virtualInitialTokenAmount(
    virtualLiquidity,
    virtualMetrics?.position_liquidity,
    virtualMetrics?.protocol_fee_amount1,
    position.virtual_initial_amount1,
  )

  return {
    liquidity: amountString(
      numericAmount(actual.liquidity) +
      numericAmount(virtualLiquidity) +
      numericAmount(virtualMetrics?.position_liquidity),
    ),
    amount0: amountString(
      numericAmount(actual.amount0) +
      numericAmount(virtualInitialAmount0) +
      numericAmount(virtualMetrics?.protocol_fee_amount0),
    ),
    amount1: amountString(
      numericAmount(actual.amount1) +
      numericAmount(virtualInitialAmount1) +
      numericAmount(virtualMetrics?.protocol_fee_amount1),
    ),
  }
}

export const positionDisplayShareRatio = (
  position: Position,
  actualMetrics: PositionMetricsEntry | undefined,
  virtualMetrics: PositionMetricsEntry | undefined,
) => {
  const actualRatio = numericAmount(actualMetrics?.share_ratio)
  const virtualProtocolRatio = numericAmount(virtualMetrics?.share_ratio)
  const totalSupply = numericAmount(virtualMetrics?.total_supply || actualMetrics?.total_supply)
  const virtualInitialRatio = totalSupply > 0
    ? numericAmount(virtualInitialLiquidity(position)) / totalSupply
    : 0
  const total = actualRatio + virtualInitialRatio + virtualProtocolRatio
  return Number.isFinite(total) ? total : 0
}

export const positiveAmount = (value: string | number | null | undefined) => {
  const numeric = numericAmount(value)
  return Number.isFinite(numeric) && numeric > 0
}

export const positionHasActualLiquidity = (position: Position) => (
  !isVirtualPosition(position) && positiveAmount(position.current_liquidity)
)

export const positionHasVirtualReference = (position: Position, owner: string) => (
  Boolean(owner && position.protocol_fee_receiver_account === owner) &&
  (
    positiveAmount(position.virtual_current_liquidity) ||
    positiveAmount(position.virtual_initial_amount0) ||
    positiveAmount(position.virtual_initial_amount1) ||
    positiveAmount(position.protocol_fee_reference_amount0) ||
    positiveAmount(position.protocol_fee_reference_amount1)
  )
)

export const hasActivePositionForPool = (
  positions: Position[],
  position: Position,
) => positions.some((candidate) => (
  positionHasActualLiquidity(candidate) &&
  candidate.pool_application === position.pool_application &&
  Number(candidate.pool_id) === Number(position.pool_id)
))

export const positionActionLabel = (
  position: Position,
  metrics: PositionMetricsEntry | undefined,
  owner: string,
  positions: Position[] = [],
) => {
  if (positionHasActualLiquidity(position)) return 'Remove'
  if (hasActivePositionForPool(positions, position)) return undefined
  if (
    isPositionProtocolFeeReceiver(position, owner) ||
    positionHasVirtualReference(position, owner) ||
    positiveAmount(metrics?.position_liquidity)
  ) return 'Remove'
  return undefined
}

export const canUsePositionAction = (
  position: Position,
  metrics: PositionMetricsEntry | undefined,
  owner: string,
  positions: Position[] = [],
) => {
  if (positionHasActualLiquidity(position)) return position.status === 'active'
  if (hasActivePositionForPool(positions, position)) return false
  if (
    !isPositionProtocolFeeReceiver(position, owner) &&
    !positionHasVirtualReference(position, owner)
  ) return false
  return Number.parseFloat(metrics?.position_liquidity || '0') > 0
}

export const positionLiquidityAmounts = (
  position: Position,
  metrics: PositionMetricsEntry | undefined,
) => {
  if (isVirtualPosition(position)) {
    return {
      liquidity: position.current_liquidity || '0',
      amount0: position.virtual_initial_amount0 || '0',
      amount1: position.virtual_initial_amount1 || '0',
    }
  }

  return {
    liquidity: metrics?.position_liquidity || position.current_liquidity || '0',
    amount0: metrics?.redeemable_amount0 || '0',
    amount1: metrics?.redeemable_amount1 || '0',
  }
}

export const positionCollectableLiquidityAmounts = (
  position: Position,
  actualMetrics: PositionMetricsEntry | undefined,
  virtualMetrics: PositionMetricsEntry | undefined,
  owner: string,
): PositionLiquidityDisplayAmounts => {
  const actual = positionLiquidityAmounts(position, actualMetrics)
  const hasOwnerVirtualMetrics = Boolean(owner && virtualMetrics?.owner === owner)
  if (
    !hasOwnerVirtualMetrics &&
    !isPositionProtocolFeeReceiver(position, owner) &&
    !positionHasVirtualReference(position, owner)
  ) {
    return actual
  }

  return {
    liquidity: amountString(numericAmount(actual.liquidity) + numericAmount(virtualMetrics?.position_liquidity)),
    amount0: amountString(numericAmount(actual.amount0) + numericAmount(virtualMetrics?.protocol_fee_amount0)),
    amount1: amountString(numericAmount(actual.amount1) + numericAmount(virtualMetrics?.protocol_fee_amount1)),
  }
}
