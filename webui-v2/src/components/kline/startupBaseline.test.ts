import { describe, expect, test } from 'bun:test'

import {
  createStartupBaselineRecorder,
  createStartupBaselineStore,
  evaluateStartupMilestone,
  formatStartupBaselineSampleAsMarkdownRow,
  formatStartupMilestoneReport,
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
        createEvent('indicators_ready', {
          requestId: 7,
          interval: '1min',
          cacheLoadMs: 20,
          firstRenderMs: 60,
          indicatorReadyMs: 95,
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
      indicatorReadyMs: 95,
      finalPointCount: 80,
    })
  })

  test('clears recorded runs for the next baseline sample', () => {
    const recorder = createStartupBaselineRecorder()

    recorder.record(createEvent('startup_begin'))
    recorder.clear()

    expect(recorder.store.runs).toEqual([])
  })

  test('captures the latest summary as a warm or cold baseline sample', () => {
    const recorder = createStartupBaselineRecorder()

    recorder.record(createEvent('startup_begin'))
    recorder.record(
      createEvent('first_render', {
        firstRenderMs: 45,
        indicatorReadyMs: 70,
        pointCount: 99,
      }),
    )

    const sample = recorder.captureLatestSample('warm', 'first pass')

    expect(sample?.requestId).toBe(1)
    expect(sample?.interval).toBe('5min')
    expect(sample?.cacheMode).toBe('warm')
    expect(sample?.firstRenderMs).toBe(45)
    expect(sample?.indicatorReadyMs).toBe(70)
    expect(sample?.finalPointCount).toBe(99)
    expect(sample?.note).toBe('first pass')
    expect(typeof sample?.capturedAt).toBe('string')
    expect(recorder.samples()).toHaveLength(1)
  })

  test('exports captured samples as markdown table rows', () => {
    const row = formatStartupBaselineSampleAsMarkdownRow({
      requestId: 1,
      interval: '1min',
      token0: 'buy',
      token1: 'sell',
      cacheMode: 'cold',
      capturedAt: '2026-04-06T00:00:00.000Z',
      cacheLoadMs: 12,
      networkFetchMs: 250,
      mergeMs: 280,
      firstRenderMs: 310,
      indicatorReadyMs: 420,
      finalPointCount: 60,
      note: 'empty cache',
    })

    expect(row).toBe(
      '| `1min` | cold | `12` | `250` | `280` | `310` | `420` | `60` | `empty cache` |',
    )
  })

  test('evaluates the feels-instant milestone against warm and cold thresholds', () => {
    const evaluation = evaluateStartupMilestone([
      {
        requestId: 1,
        interval: '1min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'warm',
        capturedAt: '2026-04-07T00:00:00.000Z',
        firstRenderMs: 220,
        finalPointCount: 120,
      },
      {
        requestId: 2,
        interval: '1min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'cold',
        capturedAt: '2026-04-07T00:01:00.000Z',
        firstRenderMs: 820,
        finalPointCount: 110,
      },
      {
        requestId: 3,
        interval: '5min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'warm',
        capturedAt: '2026-04-07T00:02:00.000Z',
        firstRenderMs: 260,
        finalPointCount: 90,
      },
      {
        requestId: 4,
        interval: '5min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'cold',
        capturedAt: '2026-04-07T00:03:00.000Z',
        firstRenderMs: 930,
        finalPointCount: 88,
      },
      {
        requestId: 5,
        interval: '10min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'warm',
        capturedAt: '2026-04-07T00:04:00.000Z',
        firstRenderMs: 280,
        finalPointCount: 72,
      },
      {
        requestId: 6,
        interval: '10min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'cold',
        capturedAt: '2026-04-07T00:05:00.000Z',
        firstRenderMs: 980,
        finalPointCount: 70,
      },
    ])

    expect(evaluation.passed).toBe(true)
    expect(evaluation.results).toHaveLength(6)
    expect(evaluation.failures).toEqual([])
  })

  test('reports missing or slow samples as milestone failures', () => {
    const evaluation = evaluateStartupMilestone([
      {
        requestId: 1,
        interval: '1min',
        token0: 'buy',
        token1: 'sell',
        cacheMode: 'warm',
        capturedAt: '2026-04-07T00:00:00.000Z',
        firstRenderMs: 420,
        finalPointCount: 120,
      },
    ])

    expect(evaluation.passed).toBe(false)
    expect(evaluation.failures.includes('warm 1min firstRenderMs 420ms exceeds target 300ms')).toBe(
      true,
    )
    expect(evaluation.failures.includes('missing cold sample for 1min')).toBe(true)
    expect(evaluation.failures.includes('missing warm sample for 5min')).toBe(true)
  })

  test('formats a stable milestone report for the task board or notes', () => {
    const report = formatStartupMilestoneReport(
      evaluateStartupMilestone([
        {
          requestId: 1,
          interval: '1min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'warm',
          capturedAt: '2026-04-07T00:00:00.000Z',
          firstRenderMs: 220,
          finalPointCount: 120,
        },
        {
          requestId: 2,
          interval: '1min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'cold',
          capturedAt: '2026-04-07T00:01:00.000Z',
          firstRenderMs: 820,
          finalPointCount: 110,
        },
        {
          requestId: 3,
          interval: '5min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'warm',
          capturedAt: '2026-04-07T00:02:00.000Z',
          firstRenderMs: 260,
          finalPointCount: 90,
        },
        {
          requestId: 4,
          interval: '5min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'cold',
          capturedAt: '2026-04-07T00:03:00.000Z',
          firstRenderMs: 930,
          finalPointCount: 88,
        },
        {
          requestId: 5,
          interval: '10min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'warm',
          capturedAt: '2026-04-07T00:04:00.000Z',
          firstRenderMs: 280,
          finalPointCount: 72,
        },
        {
          requestId: 6,
          interval: '10min',
          token0: 'buy',
          token1: 'sell',
          cacheMode: 'cold',
          capturedAt: '2026-04-07T00:05:00.000Z',
          firstRenderMs: 980,
          finalPointCount: 70,
        },
      ]),
    )

    expect(report.includes('Milestone: PASS')).toBe(true)
    expect(report.includes('| `1min` | warm | pass | `220 / 300` |')).toBe(true)
    expect(report.includes('| `10min` | cold | pass | `980 / 1000` |')).toBe(true)
  })
})
