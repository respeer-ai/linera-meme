import { describe, expect, test } from 'bun:test'

import { createStartupInstrumentation } from './startupInstrumentation'

describe('createStartupInstrumentation', () => {
  test('emits startup timings for a warm-cache startup path', () => {
    let currentNow = 0
    const events: Array<Record<string, unknown>> = []
    const instrumentation = createStartupInstrumentation({
      now: () => currentNow,
      emit: (event) => events.push(event),
    })

    instrumentation.begin({
      requestId: 7,
      interval: '5m',
      token0: 'buy',
      token1: 'sell',
    })

    currentNow = 25
    instrumentation.markCacheLoaded({ requestId: 7, pointCount: 120 })

    currentNow = 40
    instrumentation.markPointsMerged({ requestId: 7, pointCount: 120, source: 'cache' })

    currentNow = 55
    instrumentation.markFirstRender({ requestId: 7, pointCount: 120 })

    currentNow = 80
    instrumentation.markIndicatorsReady({ requestId: 7, pointCount: 120 })

    expect(events.map((event) => event.event)).toEqual([
      'startup_begin',
      'cache_loaded',
      'points_merged',
      'first_render',
      'indicators_ready',
    ])
    expect(events[1]?.cacheLoadMs).toBe(25)
    expect(events[2]?.mergeMs).toBe(40)
    expect(events[3]?.firstRenderMs).toBe(55)
    expect(events[4]?.indicatorReadyMs).toBe(80)
  })

  test('emits both cache and network milestones for a partial-cache startup path', () => {
    let currentNow = 0
    const events: Array<Record<string, unknown>> = []
    const instrumentation = createStartupInstrumentation({
      now: () => currentNow,
      emit: (event) => events.push(event),
    })

    instrumentation.begin({
      requestId: 9,
      interval: '1m',
      token0: 'buy',
      token1: 'sell',
    })

    currentNow = 10
    instrumentation.markCacheLoaded({ requestId: 9, pointCount: 80 })

    currentNow = 32
    instrumentation.markNetworkFetched({ requestId: 9, pointCount: 12 })

    currentNow = 45
    instrumentation.markPointsMerged({ requestId: 9, pointCount: 92, source: 'network' })

    currentNow = 52
    instrumentation.markFirstRender({ requestId: 9, pointCount: 92 })

    currentNow = 91
    instrumentation.markIndicatorsReady({ requestId: 9, pointCount: 92 })

    expect(events.map((event) => event.event)).toEqual([
      'startup_begin',
      'cache_loaded',
      'network_fetched',
      'points_merged',
      'first_render',
      'indicators_ready',
    ])
    expect(events[2]?.networkFetchMs).toBe(32)
    expect(events[3]?.source).toBe('network')
    expect(events[4]?.firstRenderMs).toBe(52)
    expect(events[5]?.indicatorReadyMs).toBe(91)
  })

  test('ignores milestones from stale requests', () => {
    let currentNow = 0
    const events: Array<Record<string, unknown>> = []
    const instrumentation = createStartupInstrumentation({
      now: () => currentNow,
      emit: (event) => events.push(event),
    })

    instrumentation.begin({
      requestId: 1,
      interval: '5m',
      token0: 'buy',
      token1: 'sell',
    })

    instrumentation.begin({
      requestId: 2,
      interval: '5m',
      token0: 'buy',
      token1: 'sell',
    })

    currentNow = 20
    instrumentation.markCacheLoaded({ requestId: 1, pointCount: 100 })
    instrumentation.markCacheLoaded({ requestId: 2, pointCount: 100 })

    expect(events.map((event) => event.event)).toEqual([
      'startup_begin',
      'startup_begin',
      'cache_loaded',
    ])
    expect(events[2]?.requestId).toBe(2)
  })

  test('records indicator readiness only once for the current request', () => {
    let currentNow = 0
    const events: Array<Record<string, unknown>> = []
    const instrumentation = createStartupInstrumentation({
      now: () => currentNow,
      emit: (event) => events.push(event),
    })

    instrumentation.begin({
      requestId: 4,
      interval: '5m',
      token0: 'buy',
      token1: 'sell',
    })

    currentNow = 10
    instrumentation.markFirstRender({ requestId: 4, pointCount: 100 })

    currentNow = 20
    instrumentation.markIndicatorsReady({ requestId: 4, pointCount: 100 })

    currentNow = 30
    instrumentation.markIndicatorsReady({ requestId: 4, pointCount: 100 })

    expect(events.map((event) => event.event)).toEqual([
      'startup_begin',
      'first_render',
      'indicators_ready',
    ])
    expect(events[2]?.indicatorReadyMs).toBe(20)
  })
})
