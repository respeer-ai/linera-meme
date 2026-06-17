import { describe, expect, test } from 'bun:test'

import { type Position } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'
import {
  canUsePositionAction,
  positionActionLabel,
  positionCollectableLiquidityAmounts,
  positionDisplayLiquidityAmounts,
  positionDisplayShareRatio,
  positionHasVirtualReference,
  positionKey,
  positionLiquidityAmounts,
  positionMetricsFor,
  positionMetricsKey,
  positionRewardLiquidity,
  positionRewardShareRatio,
  selectDisplayPositions,
  virtualPositionMetricsFor,
} from './positionsData'

const owner = '0xc21c@owner-chain'
const poolApplication = '0xpool@pool-chain'

const activePosition: Position = {
  pool_application: poolApplication,
  pool_id: 11,
  token_0: 'LMM',
  token_1: 'TLINERA',
  owner,
  status: 'active',
  current_liquidity: '1.200232328779602238',
  added_liquidity: '1.200232328779602238',
  removed_liquidity: '0',
  add_tx_count: 1,
  remove_tx_count: 0,
  opened_at: 1780822359133,
  updated_at: 1780822359133,
  closed_at: null,
}

const virtualPosition: Position = {
  pool_application: poolApplication,
  pool_id: 11,
  token_0: 'LMM',
  token_1: 'TLINERA',
  owner,
  status: 'virtual',
  current_liquidity: '302587.389030012286796095',
  added_liquidity: '302587.389030012286796095',
  removed_liquidity: '0',
  add_tx_count: 2,
  remove_tx_count: 0,
  opened_at: 1780556515352,
  updated_at: 1780822359133,
  closed_at: null,
  position_kind: 'virtual_initial_liquidity',
  is_virtual_position: true,
  virtual_initial_amount0: '10499900',
  virtual_initial_amount1: '8720',
  protocol_fee_receiver_account: owner,
}

const mergedVirtualOnlyPosition: Position = {
  ...activePosition,
  current_liquidity: '0',
  added_liquidity: '0',
  removed_liquidity: '0',
  status: 'active',
  virtual_current_liquidity: '302587.389030012286796095',
  virtual_initial_amount0: '10499900',
  virtual_initial_amount1: '8720',
  protocol_fee_receiver_account: owner,
  protocol_fee_reference_amount0: '29937.723',
  protocol_fee_reference_amount1: '27.164',
}

const activeMetrics: PositionMetricsEntry = {
  pool_application: poolApplication,
  pool_id: 11,
  token_0: 'LMM',
  token_1: 'TLINERA',
  owner,
  status: 'active',
  current_liquidity: '1.200232328779602238',
  position_liquidity: '1.200232328779602238',
  total_supply: '303312.222121634290873004',
  share_ratio: '0.000003957085277949',
  redeemable_amount0: '40.128472432178798483',
  redeemable_amount1: '0.036771630990749769',
  virtual_initial_liquidity: true,
  computation_blockers: [],
  principal_amount0: '40.069722459304627926',
  principal_amount1: '0.036718023713804877',
  fee_amount0: '0.058749972874170557',
  fee_amount1: '0.000053607276944892',
  protocol_fee_amount0: '0',
  protocol_fee_amount1: '0',
  trailing_24h_fee_amount0: '0.02',
  trailing_24h_fee_amount1: '0.00002',
  trailing_24h_fee_window_start_ms: 1780735959133,
  trailing_24h_fee_window_end_ms: 1780822359133,
  value_warning_codes: [],
  value_warning_message: null,
}

const virtualMetrics: PositionMetricsEntry = {
  ...activeMetrics,
  status: 'virtual',
  current_liquidity: '302587.389030012286796095',
  position_liquidity: '73.853756302460584155',
  share_ratio: '0.000243490868207888',
  redeemable_amount0: '2469.220627317689461086',
  redeemable_amount1: '2.262664493295386719',
  principal_amount0: '0',
  principal_amount1: '0',
  fee_amount0: '0',
  fee_amount1: '0',
  protocol_fee_amount0: '2469.220627317689461086',
  protocol_fee_amount1: '2.262664493295386719',
  value_warning_codes: ['virtual_initial_liquidity_protocol_fee_receiver_position'],
  value_warning_message: 'Virtual initial liquidity is pool-level, not owner-held LP.',
}

describe('positionsData', () => {
  test('keys active metrics as recorded even on a virtual-initial-liquidity pool', () => {
    expect(positionMetricsKey(activeMetrics)).toBe(`${poolApplication}:11:active:recorded`)
    expect(positionMetricsKey(virtualMetrics)).toBe(`${poolApplication}:11:virtual:virtual_initial_liquidity`)
  })

  test('matches active metrics so pooled tokens and trading fees use API values', () => {
    const snapshots = {
      [positionMetricsKey(activeMetrics)]: activeMetrics,
      [positionMetricsKey(virtualMetrics)]: virtualMetrics,
    }

    const metrics = positionMetricsFor(activePosition, snapshots)
    const liquidity = positionLiquidityAmounts(activePosition, metrics)

    expect(positionKey(activePosition)).toBe(`${poolApplication}:11:active:recorded`)
    expect(metrics?.fee_amount0).toBe('0.058749972874170557')
    expect(metrics?.fee_amount1).toBe('0.000053607276944892')
    expect(liquidity.amount0).toBe('40.128472432178798483')
    expect(liquidity.amount1).toBe('0.036771630990749769')
  })

  test('uses position metrics liquidity for the top LMM summary', () => {
    const activeLiquidity = positionRewardLiquidity(activePosition, activeMetrics, owner)
    const virtualLiquidity = positionRewardLiquidity(virtualPosition, virtualMetrics, owner)

    expect(activeLiquidity).toBe('1.200232328779602238')
    expect(virtualLiquidity).toBe('73.853756302460584155')
  })

  test('hides standalone virtual positions from the card list', () => {
    expect(selectDisplayPositions([activePosition, virtualPosition])).toEqual([activePosition])
  })

  test('shows active synthetic virtual-initial display positions in the card list', () => {
    expect(selectDisplayPositions([mergedVirtualOnlyPosition])).toEqual([mergedVirtualOnlyPosition])
  })

  test('counts merged virtual protocol-fee liquidity in the top LMM summary', () => {
    expect(positionRewardLiquidity(mergedVirtualOnlyPosition, virtualMetrics, owner)).toBe('73.853756302460584155')
    expect(positionHasVirtualReference(mergedVirtualOnlyPosition, owner)).toBe(true)
  })

  test('uses actual plus virtual share ratio for displayed pool share', () => {
    expect(positionRewardShareRatio(undefined, virtualMetrics).toFixed(18)).toBe('0.000243490868207888')
    expect(positionRewardShareRatio(activeMetrics, virtualMetrics).toFixed(18)).toBe('0.000247447953485837')
  })

  test('uses virtual initial plus protocol fee liquidity for displayed pool share', () => {
    const displayRatio = positionDisplayShareRatio(mergedVirtualOnlyPosition, undefined, virtualMetrics)

    expect(displayRatio.toFixed(18)).toBe('0.997853764906781460')
  })

  test('uses virtual initial plus protocol fee amounts for displayed pooled tokens', () => {
    const liquidity = positionDisplayLiquidityAmounts(mergedVirtualOnlyPosition, undefined, virtualMetrics)

    expect(liquidity.liquidity).toBe('302661.24278631475')
    expect(Number(liquidity.amount0).toFixed(6)).toBe('10119151.972676')
    expect(Number(liquidity.amount1).toFixed(6)).toBe('9272.661024')
  })

  test('does not use virtual bootstrap amounts as actual pooled tokens', () => {
    const liquidity = positionLiquidityAmounts(mergedVirtualOnlyPosition, undefined)

    expect(liquidity.liquidity).toBe('0')
    expect(liquidity.amount0).toBe('0')
    expect(liquidity.amount1).toBe('0')
  })

  test('collectable liquidity includes active LP plus protocol fees for the creator', () => {
    const liquidity = positionCollectableLiquidityAmounts(activePosition, activeMetrics, virtualMetrics, owner)

    expect(Number(liquidity.liquidity).toFixed(6)).toBe('75.053989')
    expect(Number(liquidity.amount0).toFixed(6)).toBe('2509.349100')
    expect(Number(liquidity.amount1).toFixed(6)).toBe('2.299436')
  })

  test('collectable liquidity excludes protocol fees for non-creator owners', () => {
    const liquidity = positionCollectableLiquidityAmounts(activePosition, activeMetrics, virtualMetrics, '0xother@owner-chain')

    expect(liquidity.liquidity).toBe('1.200232328779602238')
    expect(liquidity.amount0).toBe('40.128472432178798483')
    expect(liquidity.amount1).toBe('0.036771630990749769')
  })

  test('looks up virtual metrics by pool for a merged display position', () => {
    const snapshots = {
      [positionMetricsKey(virtualMetrics)]: virtualMetrics,
    }

    expect(virtualPositionMetricsFor(mergedVirtualOnlyPosition, snapshots)?.protocol_fee_amount0).toBe('2469.220627317689461086')
  })

  test('uses remove action for merged virtual-only display position', () => {
    expect(positionActionLabel(mergedVirtualOnlyPosition, virtualMetrics, owner, [mergedVirtualOnlyPosition])).toBe('Remove')
    expect(canUsePositionAction(mergedVirtualOnlyPosition, virtualMetrics, owner, [mergedVirtualOnlyPosition])).toBe(true)
  })

  test('uses only one withdraw action per pool when actual liquidity exists', () => {
    const positions = [activePosition, virtualPosition]

    expect(positionActionLabel(activePosition, activeMetrics, owner, positions)).toBe('Remove')
    expect(canUsePositionAction(activePosition, activeMetrics, owner, positions)).toBe(true)
    expect(positionActionLabel(virtualPosition, virtualMetrics, owner, positions)).toBe(undefined)
    expect(canUsePositionAction(virtualPosition, virtualMetrics, owner, positions)).toBe(false)
  })

  test('keeps remove action on virtual position when no actual liquidity exists', () => {
    expect(positionActionLabel(virtualPosition, virtualMetrics, owner, [virtualPosition])).toBe('Remove')
    expect(canUsePositionAction(virtualPosition, virtualMetrics, owner, [virtualPosition])).toBe(true)
  })

  test('keeps remove label disabled when no protocol-fee liquidity is available', () => {
    const emptyVirtualMetrics = {
      ...virtualMetrics,
      position_liquidity: '0',
      protocol_fee_amount0: '0',
      protocol_fee_amount1: '0',
    }

    expect(positionActionLabel(virtualPosition, emptyVirtualMetrics, owner, [virtualPosition])).toBe('Remove')
    expect(canUsePositionAction(virtualPosition, emptyVirtualMetrics, owner, [virtualPosition])).toBe(false)
  })
})
