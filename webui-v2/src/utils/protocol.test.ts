import { describe, expect, test } from 'bun:test'

import {
  applySwapFee,
  buildNativePriceMap,
  calculateConstantProductPriceImpact,
  calculatePoolAprFromDailyVolume,
  calculatePoolTvlInNative,
  calculatePoolVolumeInNative,
  calculateSwapFeeAmount,
  protocolSwapFeePercentLabel,
  protocolSwapFeeRate,
} from './protocol'
import { constants } from 'src/constant'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { type PoolStat } from 'src/stores/kline'

const nativePairPool = (
  token0: string,
  token1: string,
  token0Price: string,
  token1Price: string,
  reserve0: string,
  reserve1: string,
): Pool =>
  ({
    __typename: 'Pool',
    creator: 'creator',
    poolId: 1,
    token0,
    token1,
    poolApplication: 'pool-app',
    latestTransaction: null,
    token0Price,
    token1Price,
    reserve0,
    reserve1,
    createdAt: 0,
  }) as Pool

describe('protocol swap fee helpers', () => {
  test('exposes the fixed protocol swap fee as a shared single source of truth', () => {
    expect(protocolSwapFeeRate()).toBe(0.003)
    expect(protocolSwapFeePercentLabel()).toBe('0.3%')
  })

  test('calculates swap fee amount from the shared protocol fee rate', () => {
    expect(calculateSwapFeeAmount(100)).toBe(0.3)
    expect(calculateSwapFeeAmount(0)).toBe(0)
    expect(calculateSwapFeeAmount(-1)).toBe(0)
  })

  test('applies swap fee to the input amount using the shared protocol fee rate', () => {
    expect(applySwapFee(100)).toBe(99.7)
    expect(applySwapFee(0)).toBe(0)
  })

  test('calculates constant-product price impact with the shared fee-adjusted input amount', () => {
    const impact = calculateConstantProductPriceImpact(1000, 500, 100)
    expect(impact.toFixed(8)).toBe('0.09066109')
  })

  test('returns zero price impact when reserves or input are invalid', () => {
    expect(calculateConstantProductPriceImpact(0, 500, 100)).toBe(0)
    expect(calculateConstantProductPriceImpact(1000, 500, 0)).toBe(0)
  })

  test('annualizes pool apr from daily volume using the shared protocol fee rate', () => {
    const apr = calculatePoolAprFromDailyVolume(1000, 5000)
    expect(apr.toFixed(4)).toBe('0.2190')
  })

  test('returns zero apr when daily volume or tvl is invalid', () => {
    expect(calculatePoolAprFromDailyVolume(0, 5000)).toBe(0)
    expect(calculatePoolAprFromDailyVolume(1000, 0)).toBe(0)
  })

  test('builds a token-native price map from native-anchored pools', () => {
    const priceMap = buildNativePriceMap([
      nativePairPool('MEME', constants.LINERA_NATIVE_ID, '2.5', '0.4', '100', '250'),
      nativePairPool(constants.LINERA_NATIVE_ID, 'ALT', '0.5', '2', '300', '150'),
    ])

    expect(priceMap.get(constants.LINERA_NATIVE_ID)).toBe(1)
    expect(priceMap.get('MEME')).toBe(2.5)
    expect(priceMap.get('ALT')).toBe(2)
  })

  test('calculates pool tvl in native units only when both token valuations are known', () => {
    const priceMap = buildNativePriceMap([
      nativePairPool('MEME', constants.LINERA_NATIVE_ID, '2', '0.5', '100', '200'),
      nativePairPool('ALT', constants.LINERA_NATIVE_ID, '4', '0.25', '50', '200'),
    ])

    const nonNativePool = nativePairPool('MEME', 'ALT', '0.5', '2', '10', '5')
    const tvl = calculatePoolTvlInNative(nonNativePool, priceMap)

    expect(tvl).toBe(40)
  })

  test('does not fabricate pool tvl when native valuation is unavailable', () => {
    const priceMap = buildNativePriceMap([])
    const pool = nativePairPool('MEME', 'ALT', '0.5', '2', '10', '5')

    expect(calculatePoolTvlInNative(pool, priceMap)).toBe(undefined)
  })

  test('converts pool stat volume into native units using the token1 native price', () => {
    const priceMap = new Map<string, number>([
      [constants.LINERA_NATIVE_ID, 1],
      ['ALT', 2],
    ])
    const poolStat: PoolStat = {
      pool_id: 7,
      token_0: 'MEME',
      token_1: 'ALT',
      high: '3',
      low: '1',
      volume: '12.5',
      tx_count: 3,
      price_now: '2',
      price_start: '1.5',
    }

    expect(calculatePoolVolumeInNative(poolStat, priceMap)).toBe(25)
  })

  test('does not fabricate pool stat volume when token1 native price is unavailable', () => {
    const poolStat: PoolStat = {
      pool_id: 7,
      token_0: 'MEME',
      token_1: 'ALT',
      high: '3',
      low: '1',
      volume: '12.5',
      tx_count: 3,
      price_now: '2',
      price_start: '1.5',
    }

    expect(calculatePoolVolumeInNative(poolStat, new Map())).toBe(undefined)
  })
})
