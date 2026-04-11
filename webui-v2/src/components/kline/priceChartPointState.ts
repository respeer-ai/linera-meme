import type { KLineData } from './chart/KlineData'
import type { Point } from 'src/stores/kline/types'
import { shouldOverwriteOverlappingPoint } from 'src/worker/kline/pointMerge'

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

const toComparablePoint = (point: KLineData): Point => ({
  ...(point.is_final !== undefined ? { is_final: point.is_final } : {}),
  timestamp: point.time * 1000,
  open: point.open,
  high: point.high,
  low: point.low,
  close: point.close,
  base_volume: point.base_volume ?? point.volume,
  quote_volume: point.quote_volume ?? 0,
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

const chartPointEquals = (left: KLineData, right: KLineData): boolean =>
  left.time === right.time &&
  left.open === right.open &&
  left.high === right.high &&
  left.low === right.low &&
  left.close === right.close &&
  left.volume === right.volume

export const chartStateChanged = (currentPoints: KLineData[], nextPoints: KLineData[]): boolean => {
  if (currentPoints.length !== nextPoints.length) return true

  return currentPoints.some(
    (point, index) => !chartPointEquals(point, nextPoints[index] as KLineData),
  )
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
    .filter(
      (point) => point.timestamp >= thresholdTimestamp || currentTimestamps.has(point.timestamp),
    )
    .filter((point) => {
      const currentPoint = currentPoints.find((current) => current.time * 1000 === point.timestamp)
      if (!currentPoint) return true
      return shouldOverwriteOverlappingPoint(toComparablePoint(currentPoint), point)
    })
    .sort((left, right) => left.timestamp - right.timestamp)
}
