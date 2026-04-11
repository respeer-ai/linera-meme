import { describe, expect, test } from 'bun:test'

import type { KLineData } from './KlineData'
import {
  getChartDataRenderSignal,
  shouldAnchorLatestAfterBootstrapExpansion,
  shouldFitContentOnFirstRender,
  shouldScrollToLatestAfterIncrementalAppend,
  shouldScrollToLatestOnFirstRender,
  resolveVisibleLogicalRangeAfterPrimaryRender,
  resolveVisibleLogicalRangeRestore,
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

describe('getChartDataRenderSignal', () => {
  test('changes when a new tail bar is appended', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      ...previous,
      point(180, 2, 3, 1.8, 2.6, 15),
    ]

    expect(getChartDataRenderSignal(next) === getChartDataRenderSignal(previous)).toBe(false)
  })

  test('changes when the latest tail bar is overwritten in place', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.8, 1, 2.3, 18),
    ]

    expect(getChartDataRenderSignal(next) === getChartDataRenderSignal(previous)).toBe(false)
  })

  test('ignores deep mutations outside the tracked trailing window', () => {
    const previous = Array.from({ length: 12 }, (_, index) =>
      point((index + 1) * 60, index + 1, index + 2, index + 0.5, index + 1.5, index + 10))
    const next = previous.map((item, index) => index === 0
      ? point(item.time, item.open, item.high + 1, item.low, item.close + 1, item.volume + 10)
      : item)

    expect(getChartDataRenderSignal(next)).toBe(getChartDataRenderSignal(previous))
  })
})

describe('resolveVisibleLogicalRangeRestore', () => {
  test('keeps the same logical range for append-only updates', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      ...previous,
      point(180, 2, 3, 1.8, 2.6, 15),
    ]

    expect(resolveVisibleLogicalRangeRestore({
      previousData: previous,
      nextData: next,
      previousRange: { from: 10, to: 30 },
    })).toEqual({ from: 10, to: 30 })
  })

  test('shifts the logical range right when historical bars are prepended', () => {
    const previous = [
      point(120, 1.5, 2.5, 1, 2, 12),
      point(180, 2, 3, 1.8, 2.6, 15),
    ]
    const next = [
      point(60, 1, 2, 0.5, 1.5, 10),
      ...previous,
    ]

    expect(resolveVisibleLogicalRangeRestore({
      previousData: previous,
      nextData: next,
      previousRange: { from: 10, to: 30 },
    })).toEqual({ from: 11, to: 31 })
  })

  test('keeps the same logical range when the latest tail bar is overwritten', () => {
    const previous = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.5, 1, 2, 12),
    ]
    const next = [
      point(60, 1, 2, 0.5, 1.5, 10),
      point(120, 1.5, 2.8, 1, 2.3, 18),
    ]

    expect(resolveVisibleLogicalRangeRestore({
      previousData: previous,
      nextData: next,
      previousRange: { from: 10, to: 30 },
    })).toEqual({ from: 10, to: 30 })
  })

  test('returns null when there is no previous logical range', () => {
    expect(resolveVisibleLogicalRangeRestore({
      previousData: [point(60, 1, 2, 0.5, 1.5, 10)],
      nextData: [point(60, 1, 2, 0.5, 1.5, 10)],
      previousRange: null,
    })).toBe(null)
  })

  test('returns null when there is no previous rendered data to align against', () => {
    expect(resolveVisibleLogicalRangeRestore({
      previousData: [],
      nextData: [point(60, 1, 2, 0.5, 1.5, 10)],
      previousRange: { from: -0.5, to: 0.5 },
    })).toBe(null)
  })

  test('returns null when the new dataset no longer aligns with the previous timestamps', () => {
    expect(resolveVisibleLogicalRangeRestore({
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      nextData: [
        point(90, 1.2, 2.2, 0.7, 1.7, 11),
        point(150, 1.7, 2.7, 1.2, 2.2, 13),
      ],
      previousRange: { from: 10, to: 30 },
    })).toBe(null)
  })
})

describe('shouldScrollToLatestOnFirstRender', () => {
  test('does not auto-scroll when the initial dataset is too short to support a latest-edge anchor', () => {
    expect(shouldScrollToLatestOnFirstRender({
      previousData: [],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      previousRange: null,
      minimumDataPointsToAnchor: 14,
    })).toBe(false)
  })

  test('anchors the chart to the latest edge on the first full render once enough bars exist', () => {
    expect(shouldScrollToLatestOnFirstRender({
      previousData: [],
      nextData: Array.from({ length: 14 }, (_, index) => point(
        (index + 1) * 60,
        index + 1,
        index + 2,
        index + 0.5,
        index + 1.5,
        index + 10,
      )),
      previousRange: null,
      minimumDataPointsToAnchor: 14,
    })).toBe(true)
  })

  test('does not auto-scroll when a previous logical range already exists', () => {
    expect(shouldScrollToLatestOnFirstRender({
      previousData: [],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
      ],
      previousRange: { from: -0.5, to: 0.5 },
      minimumDataPointsToAnchor: 14,
    })).toBe(false)
  })

  test('does not treat incremental refreshes as a first-render latest anchor', () => {
    expect(shouldScrollToLatestOnFirstRender({
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      previousRange: null,
      minimumDataPointsToAnchor: 14,
    })).toBe(false)
  })
})

describe('shouldScrollToLatestAfterIncrementalAppend', () => {
  test('keeps the chart anchored when new bars append while the current range already reaches the latest edge', () => {
    expect(shouldScrollToLatestAfterIncrementalAppend({
      renderMode: 'incremental',
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
        point(180, 2, 3, 1.8, 2.6, 15),
      ],
      previousRange: { from: -8, to: 1.8 },
    })).toBe(true)
  })

  test('does not auto-scroll if the user is no longer looking at the latest edge', () => {
    expect(shouldScrollToLatestAfterIncrementalAppend({
      renderMode: 'incremental',
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
        point(180, 2, 3, 1.8, 2.6, 15),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
        point(180, 2, 3, 1.8, 2.6, 15),
        point(240, 2.6, 3.2, 2.4, 3, 18),
      ],
      previousRange: { from: 0, to: 1 },
    })).toBe(false)
  })

  test('does not auto-scroll when an incremental update only revises the latest candle in place', () => {
    expect(shouldScrollToLatestAfterIncrementalAppend({
      renderMode: 'incremental',
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.7, 1, 2.2, 20),
      ],
      previousRange: { from: -8, to: 1.8 },
    })).toBe(false)
  })
})

describe('shouldFitContentOnFirstRender', () => {
  test('fits content when the first render has too few bars for a latest-edge anchor', () => {
    expect(shouldFitContentOnFirstRender({
      previousData: [],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      previousRange: null,
      minimumDataPointsToAnchor: 14,
    })).toBe(true)
  })

  test('does not fit content once enough bars exist to anchor the latest edge', () => {
    expect(shouldFitContentOnFirstRender({
      previousData: [],
      nextData: Array.from({ length: 14 }, (_, index) => point(
        (index + 1) * 60,
        index + 1,
        index + 2,
        index + 0.5,
        index + 1.5,
        index + 10,
      )),
      previousRange: null,
      minimumDataPointsToAnchor: 14,
    })).toBe(false)
  })

  test('anchors latest when startup expands from a provisional tiny render to a full history render', () => {
    expect(shouldAnchorLatestAfterBootstrapExpansion({
      previousData: Array.from({ length: 3 }, (_, index) => point(
        (index + 1) * 60,
        index + 1,
        index + 2,
        index + 0.5,
        index + 1.5,
        index + 10,
      )),
      nextData: Array.from({ length: 40 }, (_, index) => point(
        (index + 1) * 60,
        index + 1,
        index + 2,
        index + 0.5,
        index + 1.5,
        index + 10,
      )),
      minimumDataPointsToAnchor: 4,
    })).toBe(true)
  })
})

describe('resolveVisibleLogicalRangeAfterPrimaryRender', () => {
  test('restores the logical range after a full render caused by prepended historical candles', () => {
    expect(resolveVisibleLogicalRangeAfterPrimaryRender({
      renderMode: 'full',
      previousData: [
        point(120, 1.5, 2.5, 1, 2, 12),
        point(180, 2, 3, 1.8, 2.6, 15),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
        point(180, 2, 3, 1.8, 2.6, 15),
      ],
      previousRange: { from: 0, to: 1 },
    })).toEqual({ from: 1, to: 2 })
  })

  test('does not restore a logical range for incremental renders', () => {
    expect(resolveVisibleLogicalRangeAfterPrimaryRender({
      renderMode: 'incremental',
      previousData: [
        point(60, 1, 2, 0.5, 1.5, 10),
      ],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
        point(120, 1.5, 2.5, 1, 2, 12),
      ],
      previousRange: { from: 0, to: 1 },
    })).toBe(null)
  })

  test('does not restore a logical range on the first full render', () => {
    expect(resolveVisibleLogicalRangeAfterPrimaryRender({
      renderMode: 'full',
      previousData: [],
      nextData: [
        point(60, 1, 2, 0.5, 1.5, 10),
      ],
      previousRange: null,
    })).toBe(null)
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
