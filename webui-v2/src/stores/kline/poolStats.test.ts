import { describe, expect, test } from 'bun:test'

import {
  buildPoolStatsByApplicationMap,
  buildPoolStatsMap,
  findPoolStat,
  findPoolStatByIdentity,
  normalizePoolStatId,
} from './poolStats'
import type { PoolStat } from './types'

const poolStat = (poolId: number | string): PoolStat => ({
  pool_id: poolId,
  pool_application: '0xpool-app@chain-a',
  token_0: 'MEME',
  token_1: 'TLINERA',
  high: '2',
  low: '1',
  volume: '42',
  tx_count: 3,
  price_now: '2',
  price_start: '1',
})

describe('pool stats identity helpers', () => {
  test('normalizes numeric pool ids from API and GraphQL boundaries', () => {
    expect(normalizePoolStatId(1)).toBe(1)
    expect(normalizePoolStatId('1')).toBe(1)
  })

  test('rejects invalid pool ids instead of fabricating a lookup key', () => {
    expect(normalizePoolStatId('')).toBe(undefined)
    expect(normalizePoolStatId('abc')).toBe(undefined)
    expect(normalizePoolStatId(1.5)).toBe(undefined)
  })

  test('finds API pool stats when the pool list supplies the id as a string', () => {
    const stats = buildPoolStatsMap([poolStat(1)])

    expect(findPoolStat(stats, '1')?.volume).toBe('42')
  })

  test('prefers pool application identity over pool id when stats use a projection-local id', () => {
    const stat = poolStat(1)
    const statsByPoolId = buildPoolStatsMap([stat])
    const statsByApplication = buildPoolStatsByApplicationMap([stat])

    expect(
      findPoolStatByIdentity(statsByPoolId, statsByApplication, 1000, '0xpool-app@chain-a')
        ?.volume,
    ).toBe('42')
  })
})
