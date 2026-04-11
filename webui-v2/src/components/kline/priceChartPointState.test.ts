import { describe, expect, test } from 'bun:test'

import type { KLineData } from './chart/KlineData'
import {
  chartStateChanged,
  mergeSortedPointsIntoChartState,
  selectLivePointsForChartState,
} from './priceChartPointState'

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
      currentPoints: [chartPoint(540, 100, 10), chartPoint(550, 101, 12), chartPoint(560, 102, 14)],
      sortedPoints: [sortedPoint(540_000, 100, 10)],
    })

    expect(merged.map((point) => point.time)).toEqual([540, 550, 560])
    expect(merged.find((point) => point.time === 550)?.close).toBe(101)
    expect(merged.find((point) => point.time === 560)?.close).toBe(102)
  })

  test('still lets incoming sorted points overwrite overlapping timestamps authoritatively', () => {
    const merged = mergeSortedPointsIntoChartState({
      currentPoints: [chartPoint(540, 100, 10), chartPoint(550, 101, 12)],
      sortedPoints: [sortedPoint(550_000, 105, 20), sortedPoint(560_000, 110, 25)],
    })

    expect(merged.map((point) => point.time)).toEqual([540, 550, 560])
    expect(merged.find((point) => point.time === 550)?.close).toBe(105)
    expect(merged.find((point) => point.time === 550)?.volume).toBe(20)
    expect(merged.find((point) => point.time === 560)?.close).toBe(110)
  })
})

describe('chartStateChanged', () => {
  test('returns false when a merge produces an identical chart state', () => {
    const current = [chartPoint(540, 100, 10), chartPoint(550, 101, 12)]
    const next = mergeSortedPointsIntoChartState({
      currentPoints: current,
      sortedPoints: [sortedPoint(550_000, 101, 12)],
    })

    expect(chartStateChanged(current, next)).toBe(false)
  })

  test('returns true when a merge changes an overlapping candle', () => {
    const current = [chartPoint(540, 100, 10), chartPoint(550, 101, 12)]
    const next = mergeSortedPointsIntoChartState({
      currentPoints: current,
      sortedPoints: [sortedPoint(550_000, 105, 20)],
    })

    expect(chartStateChanged(current, next)).toBe(true)
  })
})

describe('selectLivePointsForChartState', () => {
  test('keeps live points when the chart is still empty', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [],
      latestPoints: [sortedPoint(540_000, 100, 10), sortedPoint(550_000, 101, 12)],
    })

    expect(selected.map((point) => point.timestamp)).toEqual([540_000, 550_000])
  })

  test('includes recent live points that extend the latest rendered edge', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [chartPoint(540, 100, 10), chartPoint(550, 101, 12)],
      latestPoints: [sortedPoint(551_000, 102, 14)],
      liveOverlayWindowMs: 5_000,
    })

    expect(selected.map((point) => point.timestamp)).toEqual([551_000])
  })

  test('keeps overlapping recent live corrections even when they are older than the latest chart point', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [chartPoint(540, 100, 10), chartPoint(550, 101, 12), chartPoint(560, 102, 14)],
      latestPoints: [sortedPoint(550_000, 105, 20)],
      liveOverlayWindowMs: 5_000,
    })

    expect(selected.map((point) => point.timestamp)).toEqual([550_000])
  })

  test('ignores overlapping live placeholders that would regress a rendered non-zero candle', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [chartPoint(550, 101, 12)],
      latestPoints: [sortedPoint(550_000, 101, 0)],
      liveOverlayWindowMs: 5_000,
    })

    expect(selected).toEqual([])
  })

  test('ignores overlapping non-final live candles when the chart already has a final candle', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [{ ...chartPoint(550, 101, 12), is_final: true }],
      latestPoints: [{ ...sortedPoint(550_000, 102, 14), is_final: false }],
      liveOverlayWindowMs: 5_000,
    })

    expect(selected).toEqual([])
  })

  test('ignores older live points that are outside the recent overlay window and not on the chart', () => {
    const selected = selectLivePointsForChartState({
      currentPoints: [chartPoint(540, 100, 10), chartPoint(550, 101, 12), chartPoint(560, 102, 14)],
      latestPoints: [sortedPoint(530_000, 99, 8)],
      liveOverlayWindowMs: 5_000,
    })

    expect(selected).toEqual([])
  })
})
