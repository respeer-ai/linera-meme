import { describe, expect, test } from 'bun:test'

import { mergeLatestPointMaps, buildKlineSubscriptionMessage } from './liveUpdate'
import { Interval } from './const'
import type { Points } from './types'

const createPoints = (
  token_0: string,
  token_1: string,
  interval: string,
  timestamps: number[],
): Points => ({
  token_0,
  token_1,
  interval,
  start_at: timestamps[0] ?? 0,
  end_at: timestamps[timestamps.length - 1] ?? 0,
  points: timestamps.map((timestamp, index) => ({
    timestamp,
    open: index + 1,
    high: index + 1,
    low: index + 1,
    close: index + 1,
    volume: index + 1,
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
      { timestamp: 1000, open: 1, high: 1, low: 1, close: 1, volume: 1 },
      { timestamp: 2000, open: 1, high: 1, low: 1, close: 1, volume: 1 },
      { timestamp: 4000, open: 2, high: 2, low: 2, close: 2, volume: 2 },
    ])
    expect(merged.get(Interval.ONE_MINUTE)).toEqual([
      createPoints('CCC', 'DDD', Interval.ONE_MINUTE, [3000]),
    ])
  })
})

describe('buildKlineSubscriptionMessage', () => {
  test('serializes a pair-aware and interval-aware subscription request', () => {
    expect(buildKlineSubscriptionMessage('AAA', 'BBB', Interval.FIVE_MINUTE)).toEqual({
      action: 'subscribe',
      topic: 'kline',
      token_0: 'AAA',
      token_1: 'BBB',
      intervals: [Interval.FIVE_MINUTE],
    })
  })
})
