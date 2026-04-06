import { describe, expect, test } from 'bun:test'

import type { KLineData } from './KlineData'
import {
  resolvePrimarySeriesRenderPlan,
  toCandlestickPoint,
  toLinePoint,
  toVolumePoint,
} from './chartDataUpdate'

const point = (
  time: number,
  open: number,
  high: number,
  low: number,
  close: number,
  volume: number,
): KLineData => ({
  time,
  open,
  high,
  low,
  close,
  volume,
})

describe('resolvePrimarySeriesRenderPlan', () => {
  test('uses full render on first paint', () => {
    expect(resolvePrimarySeriesRenderPlan({
      previous: [],
      next: [point(60, 1, 2, 0.5, 1.5, 10)],
    })).toEqual({
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: [point(60, 1, 2, 0.5, 1.5, 10)],
    })
  })

  test('uses incremental render for append-only updates', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      ...previous,
      point(180, 2, 3, 1.8, 2.6, 15),
    ]

    expect(resolvePrimarySeriesRenderPlan({ previous, next })).toEqual({
      mode: 'incremental',
      changedFromIndex: 2,
      changedPoints: [point(180, 2, 3, 1.8, 2.6, 15)],
    })
  })

  test('uses incremental render when the latest bar is overwritten before append', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.7, 1, 2.2, 20),
      point(180, 2.2, 3, 2, 2.8, 9),
    ]

    expect(resolvePrimarySeriesRenderPlan({ previous, next })).toEqual({
      mode: 'incremental',
      changedFromIndex: 1,
      changedPoints: [
        point(120, 1.5, 2.7, 1, 2.2, 20),
        point(180, 2.2, 3, 2, 2.8, 9),
      ],
    })
  })

  test('falls back to full render when historical bars are prepended', () => {
    const previous = [
      point(120, 1.5, 2.5, 1, 2, 12),
      point(180, 2, 3, 1.8, 2.6, 15),
    ]
    const next = [
      point(60, 1, 2, 0.5, 1.5, 10),
      ...previous,
    ]

    expect(resolvePrimarySeriesRenderPlan({ previous, next })).toEqual({
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: next,
    })
  })

  test('falls back to full render when a non-tail bar changes', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
      point(180, 2, 3, 1.8, 2.6, 15),
    ]
    const next = [
      point(60, 1, 2.2, 0.5, 1.7, 11),
      point(120, 1.5, 2.5, 1, 2, 12),
      point(180, 2, 3, 1.8, 2.6, 15),
    ]

    expect(resolvePrimarySeriesRenderPlan({ previous, next })).toEqual({
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: next,
    })
  })

  test('returns noop when data is unchanged', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]

    expect(resolvePrimarySeriesRenderPlan({ previous, next: previous })).toEqual({
      mode: 'noop',
      changedFromIndex: 2,
      changedPoints: [],
    })
  })
})

describe('chart point conversion helpers', () => {
  test('maps a candle, line, and volume point with chart colors', () => {
    const data = point(60, 1, 2, 0.5, 1.5, 10)

    expect(toCandlestickPoint(data)).toEqual({
      time: 60,
      open: 1,
      high: 2,
      low: 0.5,
      close: 1.5,
    })

    expect(toLinePoint(data)).toEqual({
      time: 60,
      value: 1.5,
    })

    expect(toVolumePoint(data)).toEqual({
      time: 60,
      value: 10,
      color: '#26a69a',
    })
  })
})
