import { describe, expect, test } from 'bun:test'

import {
  createStartupBaselineRecorder,
  createStartupBaselineStore,
  summarizeStartupRun,
} from './startupBaseline'
import type { StartupInstrumentationEvent } from './startupInstrumentation'

const createEvent = (
  event: StartupInstrumentationEvent['event'],
  overrides: Partial<StartupInstrumentationEvent> = {},
): StartupInstrumentationEvent => ({
  requestId: 1,
  interval: '5min',
  token0: 'buy',
  token1: 'sell',
  event,
  elapsedMs: 10,
  ...overrides,
})

describe('startupBaseline', () => {
  test('groups instrumentation events by request id into stable runs', () => {
    const recorder = createStartupBaselineRecorder({
      store: createStartupBaselineStore(),
    })

    recorder.record(createEvent('startup_begin'))
    recorder.record(createEvent('cache_loaded', { cacheLoadMs: 25, pointCount: 120 }))
    recorder.record(createEvent('first_render', { firstRenderMs: 55, pointCount: 120 }))

    expect(recorder.store.runs).toHaveLength(1)
    expect(recorder.store.runs[0]?.events.map((event) => event.event)).toEqual([
      'startup_begin',
      'cache_loaded',
      'first_render',
    ])
  })

  test('produces stable summaries from the last event of each run', () => {
    const run = {
      requestId: 7,
      interval: '1min',
      token0: 'buy',
      token1: 'sell',
      events: [
        createEvent('startup_begin', { requestId: 7, interval: '1min', elapsedMs: 0 }),
        createEvent('cache_loaded', {
          requestId: 7,
          interval: '1min',
          cacheLoadMs: 20,
          pointCount: 80,
        }),
        createEvent('first_render', {
          requestId: 7,
          interval: '1min',
          cacheLoadMs: 20,
          firstRenderMs: 60,
          pointCount: 80,
        }),
      ],
    }

    expect(summarizeStartupRun(run)).toEqual({
      requestId: 7,
      interval: '1min',
      token0: 'buy',
      token1: 'sell',
      cacheLoadMs: 20,
      networkFetchMs: undefined,
      mergeMs: undefined,
      firstRenderMs: 60,
      finalPointCount: 80,
    })
  })

  test('clears recorded runs for the next baseline sample', () => {
    const recorder = createStartupBaselineRecorder()

    recorder.record(createEvent('startup_begin'))
    recorder.clear()

    expect(recorder.store.runs).toEqual([])
  })
})
