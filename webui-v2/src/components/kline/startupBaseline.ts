import type { StartupInstrumentationEvent } from './startupInstrumentation'

export type StartupBaselineRun = {
  requestId: number
  interval: string
  token0: string
  token1: string
  events: StartupInstrumentationEvent[]
}

export type StartupBaselineSummary = {
  requestId: number
  interval: string
  token0: string
  token1: string
  cacheLoadMs?: number
  networkFetchMs?: number
  mergeMs?: number
  firstRenderMs?: number
  finalPointCount?: number
}

export type StartupBaselineStore = {
  runs: StartupBaselineRun[]
}

type StartupBaselineRecorderOptions = {
  store?: StartupBaselineStore
}

type KlineStartupDebugGlobal = {
  store: StartupBaselineStore
  clear: () => void
  summaries: () => StartupBaselineSummary[]
}

type KlineStartupCacheDebugGlobal = {
  clearKlineCache: () => Promise<void>
}

declare global {
  interface Window {
    __klineStartupBaseline?: KlineStartupDebugGlobal
    __klineStartupCache?: KlineStartupCacheDebugGlobal
  }
}

export const createStartupBaselineStore = (): StartupBaselineStore => ({
  runs: [],
})

export const summarizeStartupRun = (run: StartupBaselineRun): StartupBaselineSummary => {
  const lastEvent = run.events[run.events.length - 1]

  const summary: StartupBaselineSummary = {
    requestId: run.requestId,
    interval: run.interval,
    token0: run.token0,
    token1: run.token1,
  }

  if (lastEvent?.cacheLoadMs !== undefined) {
    summary.cacheLoadMs = lastEvent.cacheLoadMs
  }
  if (lastEvent?.networkFetchMs !== undefined) {
    summary.networkFetchMs = lastEvent.networkFetchMs
  }
  if (lastEvent?.mergeMs !== undefined) {
    summary.mergeMs = lastEvent.mergeMs
  }
  if (lastEvent?.firstRenderMs !== undefined) {
    summary.firstRenderMs = lastEvent.firstRenderMs
  }
  if (lastEvent?.pointCount !== undefined) {
    summary.finalPointCount = lastEvent.pointCount
  }

  return summary
}

export const createStartupBaselineRecorder = ({
  store = createStartupBaselineStore(),
}: StartupBaselineRecorderOptions = {}) => {
  const record = (event: StartupInstrumentationEvent) => {
    const existingRun = store.runs.find((run) => run.requestId === event.requestId)

    if (existingRun) {
      existingRun.events.push(event)
      return
    }

    store.runs.push({
      requestId: event.requestId,
      interval: event.interval,
      token0: event.token0,
      token1: event.token1,
      events: [event],
    })
  }

  const clear = () => {
    store.runs = []
  }

  const summaries = () => store.runs.map(summarizeStartupRun)

  return {
    store,
    record,
    clear,
    summaries,
  }
}

export const installStartupBaselineDebug = (
  recorder: ReturnType<typeof createStartupBaselineRecorder>,
  clearKlineCache?: () => Promise<void>,
) => {
  if (typeof window === 'undefined') return

  window.__klineStartupBaseline = {
    store: recorder.store,
    clear: recorder.clear,
    summaries: recorder.summaries,
  }

  if (clearKlineCache) {
    window.__klineStartupCache = {
      clearKlineCache,
    }
  }
}
