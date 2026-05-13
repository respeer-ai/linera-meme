import { describe, expect, test } from 'bun:test'

import type { KLineData } from './chart/KlineData'
import {
  buildKlineSnapshotKey,
  cloneKlineSnapshot,
} from './priceChartMemorySnapshots'

describe('buildKlineSnapshotKey', () => {
  test('builds an interval-specific key for the same pool', () => {
    expect(
      buildKlineSnapshotKey({
        token0: 'token-a',
        token1: 'token-b',
        poolId: 7,
        poolApplication: 'pool-app',
        interval: '1min',
      }),
    ).toBe('token-a|token-b|7|pool-app|1min')
  })

  test('returns null when pool identity is incomplete', () => {
    expect(
      buildKlineSnapshotKey({
        token0: 'token-a',
        token1: 'token-b',
        poolId: undefined,
        poolApplication: 'pool-app',
        interval: '1min',
      }),
    ).toBe(null)
  })
})

describe('cloneKlineSnapshot', () => {
  test('clones points so restored snapshots are not mutated by later chart updates', () => {
    const points: KLineData[] = [
      {
        time: 1,
        open: 10,
        high: 11,
        low: 9,
        close: 10,
        volume: 3,
      },
    ]

    const cloned = cloneKlineSnapshot(points)
    cloned[0]!.close = 12

    expect(points[0]!.close).toBe(10)
  })
})
