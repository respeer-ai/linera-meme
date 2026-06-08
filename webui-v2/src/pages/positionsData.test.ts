import { describe, expect, test } from 'bun:test'

import { type Position } from 'src/stores/positions'
import { type PositionMetricsEntry } from 'src/stores/kline'
import {
  positionKey,
  positionLiquidityAmounts,
  positionMetricsFor,
  positionMetricsKey,
  positionRewardLiquidity,
  selectProtocolYieldPositions,
  selectRewardPositions,
  selectTradingYieldPositions,
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

  test('separates trading fees from virtual protocol yield', () => {
    const rewardPositions = selectRewardPositions([activePosition, virtualPosition], owner)
    const tradingPositions = selectTradingYieldPositions(rewardPositions)
    const protocolPositions = selectProtocolYieldPositions(rewardPositions, owner)

    expect(tradingPositions).toEqual([activePosition])
    expect(protocolPositions).toEqual([virtualPosition])
  })

  test('sums recorded liquidity and protocol-yield liquidity without using virtual principal', () => {
    const activeLiquidity = positionRewardLiquidity(activePosition, activeMetrics, owner)
    const virtualLiquidity = positionRewardLiquidity(virtualPosition, virtualMetrics, owner)

    expect((Number(activeLiquidity) + Number(virtualLiquidity)).toFixed(12)).toBe('75.053988631240')
  })
})
