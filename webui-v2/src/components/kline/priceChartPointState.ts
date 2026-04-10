import type { KLineData } from './chart/KlineData'
import type { Point } from 'src/stores/kline/types'

type MergeSortedPointsInput = {
  currentPoints: KLineData[]
  sortedPoints: Point[]
}

type SelectLivePointsInput = {
  currentPoints: KLineData[]
  latestPoints: Point[]
  liveOverlayWindowMs?: number
}

export const LIVE_POINT_OVERLAY_WINDOW_MS = 5 * 60 * 1000

const toChartPoint = (point: Point): KLineData => ({
  ...point,
  volume: point.base_volume,
  time: Math.floor(point.timestamp / 1000),
})

export const mergeSortedPointsIntoChartState = ({
  currentPoints,
  sortedPoints,
}: MergeSortedPointsInput): KLineData[] => {
  const merged = new Map<number, KLineData>()

  currentPoints.forEach((point) => {
    merged.set(point.time, point)
  })

  sortedPoints.forEach((point) => {
    merged.set(Math.floor(point.timestamp / 1000), toChartPoint(point))
  })

  return [...merged.values()].sort((left, right) => left.time - right.time)
}

export const selectLivePointsForChartState = ({
  currentPoints,
  latestPoints,
  liveOverlayWindowMs = LIVE_POINT_OVERLAY_WINDOW_MS,
}: SelectLivePointsInput): Point[] => {
  if (!currentPoints.length) {
    return [...latestPoints].sort((left, right) => left.timestamp - right.timestamp)
  }

  const currentTimestamps = new Set(currentPoints.map((point) => point.time * 1000))
  const maxTimestamp = Math.max(...currentPoints.map((point) => point.time * 1000))
  const thresholdTimestamp = maxTimestamp - liveOverlayWindowMs

  return latestPoints
    .filter((point) => (
      point.timestamp >= thresholdTimestamp ||
      currentTimestamps.has(point.timestamp)
    ))
    .sort((left, right) => left.timestamp - right.timestamp)
}
