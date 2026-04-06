type StartupEventName =
  | 'startup_begin'
  | 'cache_loaded'
  | 'network_fetched'
  | 'points_merged'
  | 'first_render'

type StartupContext = {
  requestId: number
  interval: string
  token0: string
  token1: string
}

type StartupMilestoneArgs = {
  requestId: number
  pointCount: number
}

type StartupMergeArgs = StartupMilestoneArgs & {
  source: 'cache' | 'network'
}

export type StartupInstrumentationEvent = StartupContext & {
  event: StartupEventName
  pointCount?: number
  source?: 'cache' | 'network'
  elapsedMs: number
  cacheLoadMs?: number
  networkFetchMs?: number
  mergeMs?: number
  firstRenderMs?: number
}

type StartupRun = StartupContext & {
  startedAt: number
  cacheLoadedAt?: number
  networkFetchedAt?: number
  mergedAt?: number
  firstRenderAt?: number
}

type StartupInstrumentationOptions = {
  now?: () => number
  emit?: (event: StartupInstrumentationEvent) => void
}

const noop = () => {}

export const createStartupInstrumentation = ({
  now = () => performance.now(),
  emit = noop,
}: StartupInstrumentationOptions = {}) => {
  let currentRun: StartupRun | null = null

  const buildEvent = (
    run: StartupRun,
    event: StartupEventName,
    args?: Partial<StartupMergeArgs>,
  ): StartupInstrumentationEvent => {
    const baseEvent: StartupInstrumentationEvent = {
      requestId: run.requestId,
      interval: run.interval,
      token0: run.token0,
      token1: run.token1,
      event,
      elapsedMs: now() - run.startedAt,
    }

    if (args?.pointCount !== undefined) {
      baseEvent.pointCount = args.pointCount
    }
    if (args?.source !== undefined) {
      baseEvent.source = args.source
    }
    if (run.cacheLoadedAt !== undefined) {
      baseEvent.cacheLoadMs = run.cacheLoadedAt - run.startedAt
    }
    if (run.networkFetchedAt !== undefined) {
      baseEvent.networkFetchMs = run.networkFetchedAt - run.startedAt
    }
    if (run.mergedAt !== undefined) {
      baseEvent.mergeMs = run.mergedAt - run.startedAt
    }
    if (run.firstRenderAt !== undefined) {
      baseEvent.firstRenderMs = run.firstRenderAt - run.startedAt
    }

    return baseEvent
  }

  const isCurrentRequest = (requestId: number) => currentRun?.requestId === requestId

  const begin = (context: StartupContext) => {
    currentRun = {
      ...context,
      startedAt: now(),
    }
    emit(buildEvent(currentRun, 'startup_begin'))
  }

  const markCacheLoaded = ({ requestId, pointCount }: StartupMilestoneArgs) => {
    if (!currentRun || !isCurrentRequest(requestId) || currentRun.cacheLoadedAt !== undefined) return

    currentRun.cacheLoadedAt = now()
    emit(buildEvent(currentRun, 'cache_loaded', { pointCount }))
  }

  const markNetworkFetched = ({ requestId, pointCount }: StartupMilestoneArgs) => {
    if (!currentRun || !isCurrentRequest(requestId) || currentRun.networkFetchedAt !== undefined) return

    currentRun.networkFetchedAt = now()
    emit(buildEvent(currentRun, 'network_fetched', { pointCount }))
  }

  const markPointsMerged = ({ requestId, pointCount, source }: StartupMergeArgs) => {
    if (!currentRun || !isCurrentRequest(requestId) || currentRun.mergedAt !== undefined) return

    currentRun.mergedAt = now()
    emit(buildEvent(currentRun, 'points_merged', { pointCount, source }))
  }

  const markFirstRender = ({ requestId, pointCount }: StartupMilestoneArgs) => {
    if (!currentRun || !isCurrentRequest(requestId) || currentRun.firstRenderAt !== undefined) return

    currentRun.firstRenderAt = now()
    emit(buildEvent(currentRun, 'first_render', { pointCount }))
  }

  return {
    begin,
    markCacheLoaded,
    markNetworkFetched,
    markPointsMerged,
    markFirstRender,
  }
}
