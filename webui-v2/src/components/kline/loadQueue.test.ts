import { describe, expect, test } from 'bun:test'

import { dequeueLoadDirection, enqueueLoadDirection } from './loadQueue'

describe('loadQueue', () => {
  test('keeps both refresh-time directions without duplication', () => {
    const queue = enqueueLoadDirection(
      enqueueLoadDirection([], 'old'),
      'new',
    )

    expect(enqueueLoadDirection(queue, 'old')).toEqual(['old', 'new'])
  })

  test('dequeues directions in insertion order', () => {
    const first = dequeueLoadDirection(['new', 'old'])

    expect(first).toEqual({
      next: 'new',
      remaining: ['old'],
    })

    expect(dequeueLoadDirection(first.remaining)).toEqual({
      next: 'old',
      remaining: [],
    })
  })
})
