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
  indicatorReadyMs?: number
  finalPointCount?: number
}

export type StartupBaselineCacheMode = 'warm' | 'cold'

export type StartupBaselineSample = StartupBaselineSummary & {
  cacheMode: StartupBaselineCacheMode
  capturedAt: string
  note?: string
}

export type StartupMilestoneThresholds = {
  warmFirstRenderMs: number
  coldFirstRenderMs: number
  requiredIntervals: string[]
}

export type StartupMilestoneResult = {
  interval: string
  cacheMode: StartupBaselineCacheMode
  status: 'pass' | 'fail' | 'missing'
  measuredFirstRenderMs?: number
  targetFirstRenderMs: number
  sample?: StartupBaselineSample
  reason: string
}

export type StartupMilestoneEvaluation = {
  passed: boolean
  thresholds: StartupMilestoneThresholds
  results: StartupMilestoneResult[]
  failures: string[]
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
  captureLatestSample: (
    cacheMode: StartupBaselineCacheMode,
    note?: string,
  ) => StartupBaselineSample | null
  exportMarkdownRows: () => string
  evaluateMilestone: () => StartupMilestoneEvaluation
  exportMilestoneReport: () => string
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

export const DEFAULT_STARTUP_MILESTONE_THRESHOLDS: StartupMilestoneThresholds = {
  warmFirstRenderMs: 300,
  coldFirstRenderMs: 1000,
  requiredIntervals: ['1min', '5min', '10min'],
}

export const formatStartupBaselineSampleAsMarkdownRow = (sample: StartupBaselineSample): string =>
  `| \`${sample.interval}\` | ${sample.cacheMode} | \`${sample.cacheLoadMs ?? 'TBD'}\` | \`${sample.networkFetchMs ?? 'TBD'}\` | \`${sample.mergeMs ?? 'TBD'}\` | \`${sample.firstRenderMs ?? 'TBD'}\` | \`${sample.indicatorReadyMs ?? 'TBD'}\` | \`${sample.finalPointCount ?? 'TBD'}\` | \`${sample.note ?? ''}\` |`

const milestoneTargetForCacheMode = (
  thresholds: StartupMilestoneThresholds,
  cacheMode: StartupBaselineCacheMode,
) => (cacheMode === 'warm' ? thresholds.warmFirstRenderMs : thresholds.coldFirstRenderMs)

export const evaluateStartupMilestone = (
  samples: StartupBaselineSample[],
  thresholds: StartupMilestoneThresholds = DEFAULT_STARTUP_MILESTONE_THRESHOLDS,
): StartupMilestoneEvaluation => {
  const results: StartupMilestoneResult[] = []
  const failures: string[] = []

  thresholds.requiredIntervals.forEach((interval) => {
    ;(['warm', 'cold'] as StartupBaselineCacheMode[]).forEach((cacheMode) => {
      const targetFirstRenderMs = milestoneTargetForCacheMode(thresholds, cacheMode)
      const sample = samples
        .filter((candidate) => candidate.interval === interval && candidate.cacheMode === cacheMode)
        .at(-1)

      if (!sample) {
        const reason = `missing ${cacheMode} sample for ${interval}`
        results.push({
          interval,
          cacheMode,
          status: 'missing',
          targetFirstRenderMs,
          reason,
        })
        failures.push(reason)
        return
      }

      if (sample.firstRenderMs === undefined) {
        const reason = `${cacheMode} ${interval} sample is missing firstRenderMs`
        results.push({
          interval,
          cacheMode,
          status: 'fail',
          targetFirstRenderMs,
          sample,
          reason,
        })
        failures.push(reason)
        return
      }

      if (sample.firstRenderMs > targetFirstRenderMs) {
        const reason = `${cacheMode} ${interval} firstRenderMs ${sample.firstRenderMs}ms exceeds target ${targetFirstRenderMs}ms`
        results.push({
          interval,
          cacheMode,
          status: 'fail',
          measuredFirstRenderMs: sample.firstRenderMs,
          targetFirstRenderMs,
          sample,
          reason,
        })
        failures.push(reason)
        return
      }

      results.push({
        interval,
        cacheMode,
        status: 'pass',
        measuredFirstRenderMs: sample.firstRenderMs,
        targetFirstRenderMs,
        sample,
        reason: `${cacheMode} ${interval} firstRenderMs ${sample.firstRenderMs}ms meets target ${targetFirstRenderMs}ms`,
      })
    })
  })

  return {
    passed: failures.length === 0,
    thresholds,
    results,
    failures,
  }
}

export const formatStartupMilestoneReport = (evaluation: StartupMilestoneEvaluation): string => {
  const lines = [
    `Milestone: ${evaluation.passed ? 'PASS' : 'FAIL'}`,
    '',
    '| Interval | Cache | Status | First Render | Points | Captured At |',
    '| --- | --- | --- | --- | --- | --- |',
  ]

  evaluation.results.forEach((result) => {
    lines.push(
      `| \`${result.interval}\` | ${result.cacheMode} | ${result.status} | \`${result.measuredFirstRenderMs ?? 'TBD'} / ${result.targetFirstRenderMs}\` | \`${result.sample?.finalPointCount ?? 'TBD'}\` | \`${result.sample?.capturedAt ?? 'TBD'}\` |`,
    )
  })

  if (evaluation.failures.length > 0) {
    lines.push('', 'Failures:')
    evaluation.failures.forEach((failure) => lines.push(`- ${failure}`))
  }

  return lines.join('\n')
}

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
  if (lastEvent?.indicatorReadyMs !== undefined) {
    summary.indicatorReadyMs = lastEvent.indicatorReadyMs
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

  const exportMarkdownRows = () =>
    store.samples.map(formatStartupBaselineSampleAsMarkdownRow).join('\n')

  const evaluateMilestone = () => evaluateStartupMilestone(store.samples)

  const exportMilestoneReport = () => formatStartupMilestoneReport(evaluateMilestone())

  return {
    store,
    record,
    clear,
    summaries,
    samples,
    clearSamples,
    captureLatestSample,
    exportMarkdownRows,
    evaluateMilestone,
    exportMilestoneReport,
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
    evaluateMilestone: recorder.evaluateMilestone,
    exportMilestoneReport: recorder.exportMilestoneReport,
  }

  if (clearKlineCache) {
    window.__klineStartupCache = {
      clearKlineCache,
    }
  }
}
