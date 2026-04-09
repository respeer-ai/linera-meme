import { describe, expect, test } from 'bun:test'

import { mergeKlinePoints } from './pointMerge'

const point = (timestamp: number, close: number) => ({
  timestamp,
  open: close,
  high: close,
  low: close,
  close,
  base_volume: close,
  quote_volume: close * 2,
})

describe('mergeKlinePoints', () => {
  test('allows fetch results to overwrite overlapping cached points', () => {
    const merged = mergeKlinePoints({
      originPoints: [point(1_000, 10), point(2_000, 20)],
      newPoints: [point(2_000, 25), point(3_000, 30)],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([
      point(1_000, 10),
      point(2_000, 25),
      point(3_000, 30),
    ])
  })

  test('prevents late cache load results from overwriting existing overlapping points', () => {
    const merged = mergeKlinePoints({
      originPoints: [point(1_000, 10), point(2_000, 25)],
      newPoints: [point(2_000, 20), point(3_000, 30)],
      reason: { reason: 'Load' },
    })

    expect(merged).toEqual([
      point(1_000, 10),
      point(2_000, 25),
      point(3_000, 30),
    ])
  })

  test('preserves zero-volume flat candles to keep financial time continuity', () => {
    const merged = mergeKlinePoints({
      originPoints: [
        { ...point(1_000, 10), base_volume: 5, quote_volume: 10 },
        { ...point(2_000, 10), base_volume: 0, quote_volume: 0 },
        { ...point(3_000, 10), base_volume: 0, quote_volume: 0 },
      ],
      newPoints: [
        { ...point(4_000, 12), base_volume: 7, quote_volume: 14 },
        { ...point(5_000, 12), base_volume: 0, quote_volume: 0 },
        { ...point(6_000, 12), base_volume: 0, quote_volume: 0 },
      ],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([
      { ...point(1_000, 10), base_volume: 5, quote_volume: 10 },
      { ...point(2_000, 10), base_volume: 0, quote_volume: 0 },
      { ...point(3_000, 10), base_volume: 0, quote_volume: 0 },
      { ...point(4_000, 12), base_volume: 7, quote_volume: 14 },
      { ...point(5_000, 12), base_volume: 0, quote_volume: 0 },
      { ...point(6_000, 12), base_volume: 0, quote_volume: 0 },
    ])
  })
})
