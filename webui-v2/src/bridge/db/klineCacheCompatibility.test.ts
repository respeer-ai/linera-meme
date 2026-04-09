import { describe, expect, test } from 'bun:test'

import { Interval } from 'src/stores/kline/const'

import { splitCompatibleKlinePoints, isCompatibleKlinePoint } from './klineCacheCompatibility'

const point = {
  id: 1,
  token0: 'token-a',
  token1: 'token-b',
  interval: Interval.TEN_MINUTE,
  timestamp: 1_000,
  bucket_start_ms: 1_000,
  bucket_end_ms: 1_599,
  is_final: true,
  open: 1,
  high: 2,
  low: 0.5,
  close: 1.5,
  base_volume: 10,
  quote_volume: 15,
}

describe('isCompatibleKlinePoint', () => {
  test('accepts cached points that include the current candle payload fields', () => {
    expect(isCompatibleKlinePoint(point)).toBe(true)
  })

  test('rejects legacy cached points that are missing financial candle metadata', () => {
    const legacyPoint = {
      ...point,
    }
    delete (legacyPoint as Partial<typeof legacyPoint>).quote_volume
    delete (legacyPoint as Partial<typeof legacyPoint>).bucket_start_ms
    delete (legacyPoint as Partial<typeof legacyPoint>).bucket_end_ms
    delete (legacyPoint as Partial<typeof legacyPoint>).is_final

    expect(isCompatibleKlinePoint({
      ...legacyPoint,
    })).toBe(false)
  })
})

describe('splitCompatibleKlinePoints', () => {
  test('separates stale cached points from compatible rows', () => {
    const stalePoint = {
      ...point,
      id: 2,
      timestamp: 2_000,
    }
    delete (stalePoint as Partial<typeof stalePoint>).quote_volume

    const result = splitCompatibleKlinePoints([
      point,
      stalePoint,
    ])

    expect(result.compatible).toEqual([point])
    expect(result.incompatible).toHaveLength(1)
    expect(result.incompatible[0]?.timestamp).toBe(2_000)
  })
})
