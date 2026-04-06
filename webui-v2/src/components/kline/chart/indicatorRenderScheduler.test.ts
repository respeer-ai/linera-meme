import { describe, expect, test } from 'bun:test'

import { createIndicatorRenderScheduler } from './indicatorRenderScheduler'

type TestHandle = ReturnType<typeof setTimeout> | number

describe('createIndicatorRenderScheduler', () => {
  test('schedules a deferred render for a new signature', () => {
    const scheduled: Array<() => void> = []
    const rendered: string[] = []

    const scheduler = createIndicatorRenderScheduler({
      schedule: (run) => {
        scheduled.push(run)
        return scheduled.length
      },
      cancel: () => {},
      run: (signature) => {
        rendered.push(signature)
      },
    })

    expect(scheduler.request('sig-1')).toBe(true)
    expect(rendered).toEqual([])

    scheduled[0]?.()

    expect(rendered).toEqual(['sig-1'])
    expect(scheduler.getRenderedSignature()).toBe('sig-1')
  })

  test('coalesces pending renders and keeps only the latest signature', () => {
    const scheduled = new Map<TestHandle, () => void>()
    const cancelled: TestHandle[] = []
    const rendered: string[] = []
    let nextHandle = 1

    const scheduler = createIndicatorRenderScheduler({
      schedule: (run) => {
        const handle = nextHandle
        nextHandle += 1
        scheduled.set(handle, run)
        return handle
      },
      cancel: (handle) => {
        cancelled.push(handle)
        scheduled.delete(handle)
      },
      run: (signature) => {
        rendered.push(signature)
      },
    })

    scheduler.request('sig-1')
    scheduler.request('sig-2')

    expect(cancelled).toEqual([1])
    expect(rendered).toEqual([])

    scheduled.get(2)?.()

    expect(rendered).toEqual(['sig-2'])
    expect(scheduler.getRenderedSignature()).toBe('sig-2')
  })

  test('does not reschedule when the signature is already rendered', () => {
    const scheduled: Array<() => void> = []

    const scheduler = createIndicatorRenderScheduler({
      schedule: (run) => {
        scheduled.push(run)
        return scheduled.length
      },
      cancel: () => {},
      run: () => {},
    })

    scheduler.request('sig-1')
    scheduled[0]?.()

    expect(scheduler.request('sig-1')).toBe(false)
    expect(scheduled).toHaveLength(1)
  })

  test('clears a pending render without executing it', () => {
    const scheduled = new Map<TestHandle, () => void>()
    const cancelled: TestHandle[] = []
    const rendered: string[] = []

    const scheduler = createIndicatorRenderScheduler({
      schedule: (run) => {
        scheduled.set(1, run)
        return 1
      },
      cancel: (handle) => {
        cancelled.push(handle)
        scheduled.delete(handle)
      },
      run: (signature) => {
        rendered.push(signature)
      },
    })

    scheduler.request('sig-1')
    scheduler.clear()

    expect(cancelled).toEqual([1])
    expect(rendered).toEqual([])
    expect(scheduler.getRenderedSignature()).toBe(null)
  })
})
