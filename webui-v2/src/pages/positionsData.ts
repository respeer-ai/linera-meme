import { type Position } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'

export type PositionMetricsSnapshots = Record<string, PositionMetricsEntry>

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

export const selectRewardPositions = (positions: Position[], owner: string) => (
  positions.filter((position) => (
    position.status !== 'closed' &&
    (!isVirtualPosition(position) || isPositionProtocolFeeReceiver(position, owner))
  ))
)

export const selectTradingYieldPositions = (positions: Position[]) => (
  positions.filter((position) => !isVirtualPosition(position))
)

export const selectProtocolYieldPositions = (positions: Position[], owner: string) => (
  positions.filter((position) => (
    isVirtualPosition(position) && isPositionProtocolFeeReceiver(position, owner)
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
  return position.current_liquidity || '0'
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
    amount0: metrics?.redeemable_amount0 || position.virtual_initial_amount0 || '0',
    amount1: metrics?.redeemable_amount1 || position.virtual_initial_amount1 || '0',
  }
}
