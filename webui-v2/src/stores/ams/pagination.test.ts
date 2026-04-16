import { describe, expect, test } from 'bun:test'

import {
  resolveApplicationsQueryCreatedAfter,
  resolveNextApplicationsCursor,
} from './pagination'

describe('ams pagination helpers', () => {
  test('overlaps incremental application queries by one timestamp unit', () => {
    expect(resolveApplicationsQueryCreatedAfter(undefined)).toBe(undefined)
    expect(resolveApplicationsQueryCreatedAfter(0)).toBe(0)
    expect(resolveApplicationsQueryCreatedAfter(1234)).toBe(1233)
  })

  test('continues pagination when a later createdAt appears', () => {
    expect(resolveNextApplicationsCursor(undefined, [{ createdAt: 100 }, { createdAt: 101 }])).toBe(101)
    expect(resolveNextApplicationsCursor(100, [{ createdAt: 100 }, { createdAt: 101 }])).toBe(101)
  })

  test('stops pagination when the overlapped page does not advance the cursor', () => {
    expect(resolveNextApplicationsCursor(101, [{ createdAt: 101 }])).toBe(undefined)
    expect(resolveNextApplicationsCursor(101, [{ createdAt: 100 }, { createdAt: 101 }])).toBe(undefined)
  })
})
