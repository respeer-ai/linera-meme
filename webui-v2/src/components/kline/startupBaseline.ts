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

export type StartupBaselineCacheMode = 'warm' | 'cold'

export type StartupBaselineSample = StartupBaselineSummary & {
  cacheMode: StartupBaselineCacheMode
  capturedAt: string
  note?: string
}

export type StartupBaselineStore = {
  runs: StartupBaselineRun[]
  samples: StartupBaselineSample[]
}

type StartupBaselineRecorderOptions = {
  store?: StartupBaselineStore
}

type KlineStartupDebugGlobal = {
  store: StartupBaselineStore
  clear: () => void
  summaries: () => StartupBaselineSummary[]
  samples: () => StartupBaselineSample[]
  clearSamples: () => void
  captureLatestSample: (cacheMode: StartupBaselineCacheMode, note?: string) => StartupBaselineSample | null
  exportMarkdownRows: () => string
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
  samples: [],
})

export const formatStartupBaselineSampleAsMarkdownRow = (
  sample: StartupBaselineSample,
): string => `| \`${sample.interval}\` | ${sample.cacheMode} | \`${sample.cacheLoadMs ?? 'TBD'}\` | \`${sample.networkFetchMs ?? 'TBD'}\` | \`${sample.mergeMs ?? 'TBD'}\` | \`${sample.firstRenderMs ?? 'TBD'}\` | \`${sample.finalPointCount ?? 'TBD'}\` | \`${sample.note ?? ''}\` |`

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

  const samples = () => [...store.samples]

  const clearSamples = () => {
    store.samples = []
  }

  const captureLatestSample = (
    cacheMode: StartupBaselineCacheMode,
    note?: string,
  ): StartupBaselineSample | null => {
    const latestSummary = summaries().at(-1)
    if (!latestSummary) return null

    const sample: StartupBaselineSample = {
      ...latestSummary,
      cacheMode,
      capturedAt: new Date().toISOString(),
    }

    if (note) {
      sample.note = note
    }

    store.samples.push(sample)
    return sample
  }

  const exportMarkdownRows = () => store.samples
    .map(formatStartupBaselineSampleAsMarkdownRow)
    .join('\n')

  return {
    store,
    record,
    clear,
    summaries,
    samples,
    clearSamples,
    captureLatestSample,
    exportMarkdownRows,
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
    samples: recorder.samples,
    clearSamples: recorder.clearSamples,
    captureLatestSample: recorder.captureLatestSample,
    exportMarkdownRows: recorder.exportMarkdownRows,
  }

  if (clearKlineCache) {
    window.__klineStartupCache = {
      clearKlineCache,
    }
  }
}
