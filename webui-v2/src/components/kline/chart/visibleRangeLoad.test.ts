import { describe, expect, test } from 'bun:test'

import { resolveVisibleRangeLoadDecision } from './visibleRangeLoad'

describe('resolveVisibleRangeLoadDecision', () => {
  test('prefers loading newer data when the whole cached range is visible', () => {
    expect(
      resolveVisibleRangeLoadDecision({
        range: { from: -20, to: 80 },
        dataLength: 50,
      }),
    ).toEqual({
      loadOld: true,
      loadNew: true,
      loadOrder: ['new', 'old'],
    })
  })

  test('loads older data when only the left edge is visible', () => {
    expect(
      resolveVisibleRangeLoadDecision({
        range: { from: -5, to: 20 },
        dataLength: 50,
      }),
    ).toEqual({
      loadOld: true,
      loadNew: false,
      loadOrder: ['old'],
    })
  })

  test('loads newer data when only the right edge is visible', () => {
    expect(
      resolveVisibleRangeLoadDecision({
        range: { from: 20, to: 55 },
        dataLength: 50,
      }),
    ).toEqual({
      loadOld: false,
      loadNew: true,
      loadOrder: ['new'],
    })
  })
})
