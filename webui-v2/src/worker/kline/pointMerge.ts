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

  return merged.sort((p1, p2) => p1.timestamp - p2.timestamp)
}
