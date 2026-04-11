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

const finalPoint = (timestamp: number, close: number) => ({
  ...point(timestamp, close),
  is_final: true,
})

describe('mergeKlinePoints', () => {
  test('allows fetch results to overwrite overlapping cached points', () => {
    const merged = mergeKlinePoints({
      originPoints: [point(1_000, 10), point(2_000, 20)],
      newPoints: [point(2_000, 25), point(3_000, 30)],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([point(1_000, 10), point(2_000, 25), point(3_000, 30)])
  })

  test('prevents zero-volume fetch candles from overwriting non-zero live candles', () => {
    const merged = mergeKlinePoints({
      originPoints: [{ ...point(2_000, 25), base_volume: 7, quote_volume: 14 }],
      newPoints: [{ ...point(2_000, 25), base_volume: 0, quote_volume: 0 }],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([{ ...point(2_000, 25), base_volume: 7, quote_volume: 14 }])
  })

  test('allows non-zero fetch candles to overwrite zero-volume placeholders', () => {
    const merged = mergeKlinePoints({
      originPoints: [{ ...point(2_000, 25), base_volume: 0, quote_volume: 0 }],
      newPoints: [{ ...point(2_000, 26), base_volume: 7, quote_volume: 14 }],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([{ ...point(2_000, 26), base_volume: 7, quote_volume: 14 }])
  })

  test('prevents non-final fetch candles from overwriting final candles', () => {
    const merged = mergeKlinePoints({
      originPoints: [finalPoint(2_000, 25)],
      newPoints: [{ ...point(2_000, 26), is_final: false }],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([finalPoint(2_000, 25)])
  })

  test('allows final fetch candles to overwrite non-final candles', () => {
    const merged = mergeKlinePoints({
      originPoints: [{ ...point(2_000, 25), is_final: false }],
      newPoints: [finalPoint(2_000, 26)],
      reason: { reason: 'Fetch' },
    })

    expect(merged).toEqual([finalPoint(2_000, 26)])
  })

  test('prevents late cache load results from overwriting existing overlapping points', () => {
    const merged = mergeKlinePoints({
      originPoints: [point(1_000, 10), point(2_000, 25)],
      newPoints: [point(2_000, 20), point(3_000, 30)],
      reason: { reason: 'Load' },
    })

    expect(merged).toEqual([point(1_000, 10), point(2_000, 25), point(3_000, 30)])
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
