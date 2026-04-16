import { Interval } from 'src/stores/kline/const'

export enum SortReason {
  FETCH = 'Fetch',
  LOAD = 'Load',
}

export type ReasonPayload = {
  startAt: number
  endAt: number
}

export interface Reason {
  reason: SortReason
  payload: ReasonPayload
}

type FetchSortDecisionInput = {
  reverse: boolean
  startAt: number
  endAt: number
}

export type FetchSortDecision = {
  reverse: boolean
  reason: Reason
}

type LoadRangeInput = {
  timestampBegin: number | undefined
  timestampEnd: number | undefined
}

export type LoadRange = {
  timestampBegin: number | undefined
  timestampEnd: number | undefined
}

export type StartupFetchRequest = {
  reverse: boolean
  startAt: number
  endAt: number
}

export type StartupCatchupFetchRequest = StartupFetchRequest

export type StartupGapBackfillFetchRequest = StartupFetchRequest & {
  key: string
}

type EdgeFetchWindowInput = {
  anchorTimestamp: number
  reverse: boolean
  windowSize: number
  nowMs: number
}

type StartupRequestPlanInput = {
  nowMs: number
  interval: Interval
  poolCreatedAt: number
}

export type StartupRequestPlan = {
  load: LoadRange & {
    reverse: boolean
    offset: number
    limit: number
  }
  fetchLatest: StartupFetchRequest
}

type StartupCatchupFetchInput = {
  cacheLatestTimestamp: number
  latestWindowStart: number
  latestWindowEnd: number
  interval: Interval
}

type StartupGapBackfillInput = {
  pointTimestamps: number[]
  latestWindowStart: number
  latestWindowEnd: number
  interval: Interval
  requestedKeys: Set<string>
}

type HistoryLoadDeferralInput = {
  direction: 'new' | 'old'
  firstScreenReady: boolean
}

type BackgroundHistoryScheduleInput = {
  firstScreenReady: boolean
  backgroundHistoryQueued: boolean
  minPointTimestamp: number
  poolCreatedAt: number
  latestWindowStart: number
}

type BackgroundHistoryStatusInput = {
  firstScreenReady: boolean
  backgroundHistoryQueued: boolean
  loadingDirection: 'new' | 'old' | null
  minPointTimestamp: number
  poolCreatedAt: number
}

type CachedRangeRefreshInput = {
  isStartupCacheLoad: boolean
  pointCount: number
  timestampBegin: number | undefined
  timestampEnd: number | undefined
}

export type BackgroundHistoryStatus = 'idle' | 'queued' | 'loading' | 'complete'

export const getFirstScreenFetchWindowSize = (interval: Interval): number => {
  switch (interval) {
    case Interval.ONE_MINUTE:
      return 1 * 3600 * 1000
    case Interval.FIVE_MINUTE:
      return 5 * 3600 * 1000
    case Interval.TEN_MINUTE:
      return 10 * 3600 * 1000
    case Interval.FIFTEEN_MINUTE:
      return 15 * 3600 * 1000
    case Interval.ONE_HOUR:
      return 24 * 3600 * 1000
    case Interval.FOUR_HOUR:
      return 4 * 24 * 3600 * 1000
    case Interval.ONE_DAY:
      return 30 * 24 * 3600 * 1000
    case Interval.ONE_MONTH:
      return 365 * 24 * 3600 * 1000
    default:
      return 1 * 3600 * 1000
  }
}

export const getIntervalBucketSize = (interval: Interval): number => {
  switch (interval) {
    case Interval.ONE_MINUTE:
      return 60 * 1000
    case Interval.FIVE_MINUTE:
      return 5 * 60 * 1000
    case Interval.TEN_MINUTE:
      return 10 * 60 * 1000
    case Interval.FIFTEEN_MINUTE:
      return 15 * 60 * 1000
    case Interval.ONE_HOUR:
      return 60 * 60 * 1000
    case Interval.FOUR_HOUR:
      return 4 * 60 * 60 * 1000
    case Interval.ONE_DAY:
      return 24 * 60 * 60 * 1000
    case Interval.ONE_MONTH:
      return 30 * 24 * 60 * 60 * 1000
    default:
      return 60 * 1000
  }
}

export const shouldDeferHistoryLoadUntilFirstPaint = ({
  direction,
  firstScreenReady,
}: HistoryLoadDeferralInput): boolean => direction === 'old' && !firstScreenReady

export const shouldScheduleBackgroundHistoryBackfill = ({
  firstScreenReady,
  backgroundHistoryQueued,
  minPointTimestamp,
  poolCreatedAt,
  latestWindowStart,
}: BackgroundHistoryScheduleInput): boolean =>
  firstScreenReady &&
  !backgroundHistoryQueued &&
  minPointTimestamp > poolCreatedAt &&
  minPointTimestamp < latestWindowStart

export const resolveBackgroundHistoryStatus = ({
  firstScreenReady,
  backgroundHistoryQueued,
  loadingDirection,
  minPointTimestamp,
  poolCreatedAt,
}: BackgroundHistoryStatusInput): BackgroundHistoryStatus => {
  if (!firstScreenReady) return 'idle'
  if (loadingDirection === 'old') return 'loading'
  if (backgroundHistoryQueued) return 'queued'
  if (minPointTimestamp <= poolCreatedAt) return 'complete'
  return 'idle'
}

export const shouldRestartKlineOnSelectedPoolChange = ({
  previousPoolId,
  nextPoolId,
  previousPoolApplication,
  nextPoolApplication,
}: {
  previousPoolId: number | undefined
  nextPoolId: number | undefined
  previousPoolApplication: string | undefined
  nextPoolApplication: string | undefined
}) =>
  nextPoolId !== undefined &&
  nextPoolApplication !== undefined &&
  (previousPoolId !== nextPoolId || previousPoolApplication !== nextPoolApplication)

type NextFetchDecisionInput = {
  reverse: boolean
  reason: Reason
  minPointTimestamp: number
  maxPointTimestamp: number
}

type StartupEmptyResultContinuationInput = {
  firstScreenReady: boolean
  reverse: boolean
}

export const resolveNextFetchTimestamp = ({
  reverse,
  reason,
  minPointTimestamp,
  maxPointTimestamp,
}: NextFetchDecisionInput): number => {
  if (reason.reason === SortReason.FETCH) {
    return reverse ? reason.payload.startAt : reason.payload.endAt
  }

  return reverse ? minPointTimestamp : maxPointTimestamp
}

export const shouldContinueStartupFetchAfterEmptyResult = ({
  firstScreenReady,
  reverse,
}: StartupEmptyResultContinuationInput): boolean => firstScreenReady || reverse === false

export const shouldRefreshCachedRangeFromNetwork = ({
  isStartupCacheLoad,
  pointCount,
  timestampBegin,
  timestampEnd,
}: CachedRangeRefreshInput): boolean =>
  !isStartupCacheLoad &&
  pointCount > 0 &&
  timestampBegin !== undefined &&
  timestampEnd !== undefined

export const resolveFetchSortDecision = ({
  reverse,
  startAt,
  endAt,
}: FetchSortDecisionInput): FetchSortDecision => ({
  reverse,
  reason: {
    reason: SortReason.FETCH,
    payload: {
      startAt,
      endAt,
    },
  },
})

export const resolveLoadRange = ({ timestampBegin, timestampEnd }: LoadRangeInput): LoadRange => ({
  timestampBegin,
  timestampEnd,
})

export const resolveStartupRequestPlan = ({
  nowMs,
  interval,
  poolCreatedAt,
}: StartupRequestPlanInput): StartupRequestPlan => {
  const windowSize = getFirstScreenFetchWindowSize(interval)
  const latestWindowStart = Math.max(poolCreatedAt, nowMs - windowSize)

  return {
    load: {
      offset: 0,
      limit: 100,
      reverse: true,
      timestampBegin: undefined,
      timestampEnd: undefined,
    },
    fetchLatest: {
      reverse: false,
      startAt: latestWindowStart,
      endAt: nowMs,
    },
  }
}

export const resolveEdgeFetchWindow = ({
  anchorTimestamp,
  reverse,
  windowSize,
  nowMs,
}: EdgeFetchWindowInput): StartupFetchRequest | null => {
  if (reverse) {
    return {
      reverse: true,
      startAt: anchorTimestamp - windowSize,
      endAt: anchorTimestamp - 1,
    }
  }

  const startAt = anchorTimestamp + 1
  const endAt = Math.min(anchorTimestamp + windowSize, nowMs)

  if (endAt < startAt) return null

  return {
    reverse: false,
    startAt,
    endAt,
  }
}

export const resolveStartupCatchupFetch = ({
  cacheLatestTimestamp,
  latestWindowStart,
  latestWindowEnd,
  interval,
}: StartupCatchupFetchInput): StartupCatchupFetchRequest | null => {
  const bucketSize = getIntervalBucketSize(interval)
  const catchupStart = Math.max(cacheLatestTimestamp + 1, latestWindowStart)
  const catchupEnd = latestWindowEnd

  if (cacheLatestTimestamp >= latestWindowEnd - bucketSize) return null
  if (catchupEnd < catchupStart) return null

  return {
    reverse: false,
    startAt: catchupStart,
    endAt: catchupEnd,
  }
}

export const resolveStartupGapBackfillFetch = ({
  pointTimestamps,
  latestWindowStart,
  latestWindowEnd,
  interval,
  requestedKeys,
}: StartupGapBackfillInput): StartupGapBackfillFetchRequest | null => {
  if (pointTimestamps.length === 0) return null

  const bucketSize = getIntervalBucketSize(interval)
  const timestamps = [...pointTimestamps]
    .filter((timestamp) => timestamp >= latestWindowStart && timestamp <= latestWindowEnd)
    .sort((left, right) => left - right)

  if (timestamps.length === 0) return null

  const firstTimestamp = timestamps[0]
  if (firstTimestamp !== undefined && firstTimestamp - latestWindowStart > bucketSize) {
    const startAt = latestWindowStart
    const endAt = firstTimestamp - 1
    const key = `${startAt}:${endAt}`
    if (!requestedKeys.has(key) && endAt >= startAt) {
      return { reverse: false, startAt, endAt, key }
    }
  }

  for (let index = 1; index < timestamps.length; index += 1) {
    const previous = timestamps[index - 1]
    const current = timestamps[index]

    if (previous === undefined || current === undefined) continue
    if (current - previous <= bucketSize) continue

    const startAt = previous + bucketSize
    const endAt = current - 1
    const key = `${startAt}:${endAt}`

    if (requestedKeys.has(key) || endAt < startAt) continue

    return {
      reverse: false,
      startAt,
      endAt,
      key,
    }
  }

  const lastTimestamp = timestamps[timestamps.length - 1]
  if (lastTimestamp !== undefined && latestWindowEnd - lastTimestamp > bucketSize) {
    const startAt = lastTimestamp + bucketSize
    const endAt = latestWindowEnd
    const key = `${startAt}:${endAt}`
    if (!requestedKeys.has(key) && endAt >= startAt) {
      return { reverse: false, startAt, endAt, key }
    }
  }

  return null
}
