import { describe, expect, test } from 'bun:test'

import {
  resolveFetchSortDecision,
  resolveLoadRange,
  resolveNextFetchTimestamp,
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
})
