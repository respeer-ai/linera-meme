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

type StartupRequestPlanInput = {
  nowMs: number
  windowSize: number
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

type NextFetchDecisionInput = {
  reverse: boolean
  reason: Reason
  minPointTimestamp: number
  maxPointTimestamp: number
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

export const resolveLoadRange = ({
  timestampBegin,
  timestampEnd,
}: LoadRangeInput): LoadRange => ({
  timestampBegin,
  timestampEnd,
})

export const resolveStartupRequestPlan = ({
  nowMs,
  windowSize,
  poolCreatedAt,
}: StartupRequestPlanInput): StartupRequestPlan => {
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
