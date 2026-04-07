import { type Point } from 'src/stores/kline/types'

type SortReasonLike = {
  reason?: string
}

type MergePointsInput = {
  originPoints: Point[]
  newPoints: Point[]
  reason: SortReasonLike
}

const isFetchReason = (reason: SortReasonLike) => reason.reason === 'Fetch'

const isSyntheticEmptyPoint = (point: Point) => (
  point.volume === 0 &&
  point.open === point.high &&
  point.high === point.low &&
  point.low === point.close
)

const filterSyntheticEmptyPoints = (points: Point[]): Point[] => (
  points.filter((point) => !isSyntheticEmptyPoint(point))
)

export const mergeKlinePoints = ({
  originPoints,
  newPoints,
  reason,
}: MergePointsInput): Point[] => {
  const merged = [...originPoints]

  newPoints.forEach((point) => {
    const index = merged.findIndex((el) => el.timestamp === point.timestamp)

    if (index < 0) {
      merged.push(point)
      return
    }

    // Network fetch is authoritative for overlapping timestamps.
    // Cache load only fills gaps and must not overwrite newer in-memory points.
    if (isFetchReason(reason)) {
      merged[index] = point
    }
  })

  return filterSyntheticEmptyPoints(
    merged.sort((p1, p2) => p1.timestamp - p2.timestamp),
  )
}
