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

const isFinal = (point: Point) => point.is_final === true

const volumeValue = (point: Point) => point.base_volume

const shouldOverwriteWithFetch = (current: Point, incoming: Point): boolean => {
  if (isFinal(current) && !isFinal(incoming)) return false
  if (volumeValue(current) > 0 && volumeValue(incoming) === 0) return false
  return true
}

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
      if (shouldOverwriteWithFetch(merged[index] as Point, point)) {
        merged[index] = point
      }
    }
  })

  return merged.sort((p1, p2) => p1.timestamp - p2.timestamp)
}
