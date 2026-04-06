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
