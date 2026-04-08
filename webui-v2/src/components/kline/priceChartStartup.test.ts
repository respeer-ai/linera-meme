import { describe, expect, test } from 'bun:test'
import { Interval } from 'src/stores/kline/const'

import {
  getFirstScreenFetchWindowSize,
  resolveFetchSortDecision,
  resolveLoadRange,
  resolveNextFetchTimestamp,
  resolveBackgroundHistoryStatus,
  resolveStartupRequestPlan,
  shouldRestartKlineOnSelectedPoolChange,
  shouldDeferHistoryLoadUntilFirstPaint,
  shouldScheduleBackgroundHistoryBackfill,
  SortReason,
  type Reason
} from './priceChartStartup'

const createReason = (reason: SortReason, startAt: number, endAt: number): Reason => ({
  reason,
  payload: {
    startAt,
    endAt,
  },
})

describe('resolveNextFetchTimestamp', () => {
  test('uses the oldest loaded point when continuing reverse load without new unique points', () => {
    const timestamp = resolveNextFetchTimestamp({
      reverse: true,
      reason: createReason(SortReason.LOAD, 1_000, 2_000),
      minPointTimestamp: 10_000,
      maxPointTimestamp: 90_000,
    })

    expect(timestamp).toBe(10_000)
  })

  test('uses the newest loaded point when continuing forward load without new unique points', () => {
    const timestamp = resolveNextFetchTimestamp({
      reverse: false,
      reason: createReason(SortReason.LOAD, 1_000, 2_000),
      minPointTimestamp: 10_000,
      maxPointTimestamp: 90_000,
    })

    expect(timestamp).toBe(90_000)
  })

  test('keeps fetch continuation anchored to the fetch range edge', () => {
    expect(resolveNextFetchTimestamp({
      reverse: true,
      reason: createReason(SortReason.FETCH, 12_345, 67_890),
      minPointTimestamp: 10_000,
      maxPointTimestamp: 90_000,
    })).toBe(12_345)

    expect(resolveNextFetchTimestamp({
      reverse: false,
      reason: createReason(SortReason.FETCH, 12_345, 67_890),
      minPointTimestamp: 10_000,
      maxPointTimestamp: 90_000,
    })).toBe(67_890)
  })

  test('preserves forward fetch direction when building sort input', () => {
    expect(resolveFetchSortDecision({
      reverse: false,
      startAt: 12_345,
      endAt: 67_890,
    })).toEqual({
      reverse: false,
      reason: createReason(SortReason.FETCH, 12_345, 67_890),
    })
  })

  test('preserves undefined load bounds so indexeddb can read the full cached range', () => {
    expect(resolveLoadRange({
      timestampBegin: undefined,
      timestampEnd: undefined,
    })).toEqual({
      timestampBegin: undefined,
      timestampEnd: undefined,
    })
  })

  test('builds a parallel startup plan with full cache load and latest-window fetch', () => {
    expect(resolveStartupRequestPlan({
      nowMs: 1_000_000,
      interval: Interval.FIVE_MINUTE,
      poolCreatedAt: 100_000,
    })).toEqual({
      load: {
        offset: 0,
        limit: 100,
        reverse: true,
        timestampBegin: undefined,
        timestampEnd: undefined,
      },
      fetchLatest: {
        reverse: false,
        startAt: 100_000,
        endAt: 1_000_000,
      },
    })
  })

  test('clamps the startup latest-window fetch to pool creation time', () => {
    expect(resolveStartupRequestPlan({
      nowMs: 1_000_000,
      interval: Interval.ONE_MINUTE,
      poolCreatedAt: 900_000,
    }).fetchLatest).toEqual({
      reverse: false,
      startAt: 900_000,
      endAt: 1_000_000,
    })
  })

  test('defines an explicit first-screen fetch window per interval', () => {
    expect(getFirstScreenFetchWindowSize(Interval.ONE_MINUTE)).toBe(1 * 3600 * 1000)
    expect(getFirstScreenFetchWindowSize(Interval.FIVE_MINUTE)).toBe(5 * 3600 * 1000)
    expect(getFirstScreenFetchWindowSize(Interval.TEN_MINUTE)).toBe(10 * 3600 * 1000)
    expect(getFirstScreenFetchWindowSize(Interval.ONE_HOUR)).toBe(24 * 3600 * 1000)
  })

  test('defers old-history loads until first paint is ready', () => {
    expect(shouldDeferHistoryLoadUntilFirstPaint({
      direction: 'old',
      firstScreenReady: false,
    })).toBe(true)

    expect(shouldDeferHistoryLoadUntilFirstPaint({
      direction: 'new',
      firstScreenReady: false,
    })).toBe(false)
  })

  test('schedules one background history backfill only after first paint', () => {
    expect(shouldScheduleBackgroundHistoryBackfill({
      firstScreenReady: true,
      backgroundHistoryQueued: false,
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe(true)

    expect(shouldScheduleBackgroundHistoryBackfill({
      firstScreenReady: false,
      backgroundHistoryQueued: false,
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe(false)

    expect(shouldScheduleBackgroundHistoryBackfill({
      firstScreenReady: true,
      backgroundHistoryQueued: true,
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe(false)
  })

  test('derives explicit background-history status for the chart', () => {
    expect(resolveBackgroundHistoryStatus({
      firstScreenReady: false,
      backgroundHistoryQueued: false,
      loadingDirection: null,
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe('idle')

    expect(resolveBackgroundHistoryStatus({
      firstScreenReady: true,
      backgroundHistoryQueued: true,
      loadingDirection: null,
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe('queued')

    expect(resolveBackgroundHistoryStatus({
      firstScreenReady: true,
      backgroundHistoryQueued: false,
      loadingDirection: 'old',
      minPointTimestamp: 2_000,
      poolCreatedAt: 1_000,
    })).toBe('loading')

    expect(resolveBackgroundHistoryStatus({
      firstScreenReady: true,
      backgroundHistoryQueued: false,
      loadingDirection: null,
      minPointTimestamp: 1_000,
      poolCreatedAt: 1_000,
    })).toBe('complete')
  })

  test('restarts kline only when the selected pool identity really changes', () => {
    expect(shouldRestartKlineOnSelectedPoolChange({
      previousPoolId: undefined,
      nextPoolId: 1,
    })).toBe(true)

    expect(shouldRestartKlineOnSelectedPoolChange({
      previousPoolId: 1,
      nextPoolId: 1,
    })).toBe(false)

    expect(shouldRestartKlineOnSelectedPoolChange({
      previousPoolId: 1,
      nextPoolId: 2,
    })).toBe(true)
  })
})
