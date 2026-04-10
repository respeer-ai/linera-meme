import { describe, expect, test } from 'bun:test'

import { mergeLatestPointMaps, buildKlineSubscriptionMessage } from './liveUpdate'
import { Interval } from './const'
import type { Points } from './types'

const createPoints = (
  token_0: string,
  token_1: string,
  interval: string,
  timestamps: number[],
  pool_id = 1,
  pool_application = 'chain:owner',
): Points => ({
  pool_id,
  pool_application,
  token_0,
  token_1,
  interval,
  start_at: timestamps[0] ?? 0,
  end_at: timestamps[timestamps.length - 1] ?? 0,
  points: timestamps.map((timestamp, index) => ({
    timestamp,
    bucket_start_ms: timestamp,
    bucket_end_ms: timestamp + 59_999,
    is_final: true,
    open: index + 1,
    high: index + 1,
    low: index + 1,
    close: index + 1,
    base_volume: index + 1,
    quote_volume: (index + 1) * 2,
  })),
})

describe('mergeLatestPointMaps', () => {
  test('preserves unrelated interval and pair entries while merging incremental candle updates', () => {
    const current = new Map([
      [Interval.FIVE_MINUTE, [createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [1000, 2000])]],
      [Interval.ONE_MINUTE, [createPoints('CCC', 'DDD', Interval.ONE_MINUTE, [3000])]],
    ])
    const incoming = new Map([
      [Interval.FIVE_MINUTE, [createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [2000, 4000])]],
    ])

    const merged = mergeLatestPointMaps(current, incoming)
    const mergedFiveMinutePoints = merged.get(Interval.FIVE_MINUTE)?.[0]?.points

    expect(mergedFiveMinutePoints === undefined).toBe(false)

    expect(mergedFiveMinutePoints).toEqual([
      { timestamp: 1000, bucket_start_ms: 1000, bucket_end_ms: 60_999, is_final: true, open: 1, high: 1, low: 1, close: 1, base_volume: 1, quote_volume: 2 },
      { timestamp: 2000, bucket_start_ms: 2000, bucket_end_ms: 61_999, is_final: true, open: 1, high: 1, low: 1, close: 1, base_volume: 1, quote_volume: 2 },
      { timestamp: 4000, bucket_start_ms: 4000, bucket_end_ms: 63_999, is_final: true, open: 2, high: 2, low: 2, close: 2, base_volume: 2, quote_volume: 4 },
    ])
    expect(merged.get(Interval.ONE_MINUTE)).toEqual([
      createPoints('CCC', 'DDD', Interval.ONE_MINUTE, [3000]),
    ])
  })

  test('keeps same-pair entries isolated when they come from different pools', () => {
    const current = new Map([
      [Interval.FIVE_MINUTE, [createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [1000], 1, 'chain:a')]],
    ])
    const incoming = new Map([
      [Interval.FIVE_MINUTE, [createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [2000], 2, 'chain:b')]],
    ])

    const merged = mergeLatestPointMaps(current, incoming)

    expect(merged.get(Interval.FIVE_MINUTE)).toEqual([
      createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [1000], 1, 'chain:a'),
      createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [2000], 2, 'chain:b'),
    ])
  })
})

describe('buildKlineSubscriptionMessage', () => {
  test('serializes a pair-aware and interval-aware subscription request', () => {
    expect(buildKlineSubscriptionMessage('AAA', 'BBB', Interval.FIVE_MINUTE, 7, 'chain:owner')).toEqual({
      action: 'subscribe',
      topic: 'kline',
      token_0: 'AAA',
      token_1: 'BBB',
      pool_id: 7,
      pool_application: 'chain:owner',
      intervals: [Interval.FIVE_MINUTE],
    })
  })

  test('retains explicit candle finality metadata when merging websocket updates', () => {
    const current = new Map([
      [Interval.FIVE_MINUTE, [{
        ...createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [1000]),
        points: [{
          timestamp: 1000,
          bucket_start_ms: 1000,
          bucket_end_ms: 1000 + 299_999,
          is_final: false,
          open: 1,
          high: 1,
          low: 1,
          close: 1,
          base_volume: 1,
          quote_volume: 2,
        }],
      }]],
    ])
    const incoming = new Map([
      [Interval.FIVE_MINUTE, [{
        ...createPoints('AAA', 'BBB', Interval.FIVE_MINUTE, [1000]),
        points: [{
          timestamp: 1000,
          bucket_start_ms: 1000,
          bucket_end_ms: 1000 + 299_999,
          is_final: true,
          open: 2,
          high: 2,
          low: 2,
          close: 2,
          base_volume: 2,
          quote_volume: 4,
        }],
      }]],
    ])

    const merged = mergeLatestPointMaps(current, incoming)
    const point = merged.get(Interval.FIVE_MINUTE)?.[0]?.points[0]

    expect(point?.is_final).toBe(true)
    expect(point?.bucket_end_ms).toBe(300999)
    expect(point?.close).toBe(2)
  })
})
