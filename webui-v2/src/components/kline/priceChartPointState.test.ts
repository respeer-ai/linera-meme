import { describe, expect, test } from 'bun:test'

import type { KLineData } from './chart/KlineData'
import { mergeSortedPointsIntoChartState } from './priceChartPointState'

const chartPoint = (time: number, close: number, volume = close): KLineData => ({
  time,
  open: close,
  high: close,
  low: close,
  close,
  volume,
  base_volume: volume,
  quote_volume: volume * 2,
})

const sortedPoint = (timestamp: number, close: number, volume = close) => ({
  timestamp,
  open: close,
  high: close,
  low: close,
  close,
  base_volume: volume,
  quote_volume: volume * 2,
  bucket_start_ms: timestamp,
  bucket_end_ms: timestamp + 1,
  is_final: true,
})

describe('mergeSortedPointsIntoChartState', () => {
  test('preserves points already rendered when a stale startup load arrives later', () => {
    const merged = mergeSortedPointsIntoChartState({
      currentPoints: [
        chartPoint(540, 100, 10),
        chartPoint(550, 101, 12),
        chartPoint(560, 102, 14),
      ],
      sortedPoints: [
        sortedPoint(540_000, 100, 10),
      ],
    })

    expect(merged.map((point) => point.time)).toEqual([540, 550, 560])
    expect(merged.find((point) => point.time === 550)?.close).toBe(101)
    expect(merged.find((point) => point.time === 560)?.close).toBe(102)
  })

  test('still lets incoming sorted points overwrite overlapping timestamps authoritatively', () => {
    const merged = mergeSortedPointsIntoChartState({
      currentPoints: [
        chartPoint(540, 100, 10),
        chartPoint(550, 101, 12),
      ],
      sortedPoints: [
        sortedPoint(550_000, 105, 20),
        sortedPoint(560_000, 110, 25),
      ],
    })

    expect(merged.map((point) => point.time)).toEqual([540, 550, 560])
    expect(merged.find((point) => point.time === 550)?.close).toBe(105)
    expect(merged.find((point) => point.time === 550)?.volume).toBe(20)
    expect(merged.find((point) => point.time === 560)?.close).toBe(110)
  })
})
