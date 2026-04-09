import type { KLineData } from './chart/KlineData'
import type { Point } from 'src/stores/kline/types'

type MergeSortedPointsInput = {
  currentPoints: KLineData[]
  sortedPoints: Point[]
}

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
