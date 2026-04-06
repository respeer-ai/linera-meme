import type { CandlestickData, HistogramData, LineData, Time } from 'lightweight-charts'

import type { KLineData } from './KlineData'

export type PrimarySeriesRenderPlan =
  | {
      mode: 'full'
      changedFromIndex: number
      changedPoints: KLineData[]
    }
  | {
      mode: 'incremental'
      changedFromIndex: number
      changedPoints: KLineData[]
    }
  | {
      mode: 'noop'
      changedFromIndex: number
      changedPoints: KLineData[]
    }

const pointsEqual = (left: KLineData, right: KLineData) => (
  left.time === right.time &&
  left.open === right.open &&
  left.high === right.high &&
  left.low === right.low &&
  left.close === right.close &&
  left.volume === right.volume
)

export const resolvePrimarySeriesRenderPlan = ({
  previous,
  next,
}: {
  previous: KLineData[]
  next: KLineData[]
}): PrimarySeriesRenderPlan => {
  if (!next.length) {
    return {
      mode: previous.length ? 'full' : 'noop',
      changedFromIndex: 0,
      changedPoints: [],
    }
  }

  if (!previous.length) {
    return {
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: next,
    }
  }

  if (next.length < previous.length) {
    return {
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: next,
    }
  }

  let changedFromIndex = next.length

  for (let index = 0; index < previous.length; index += 1) {
    const previousPoint = previous[index]
    const nextPoint = next[index]

    if (!previousPoint || !nextPoint || previousPoint.time !== nextPoint.time) {
      return {
        mode: 'full',
        changedFromIndex: 0,
        changedPoints: next,
      }
    }

    if (!pointsEqual(previousPoint, nextPoint)) {
      changedFromIndex = index
      break
    }
  }

  if (changedFromIndex === next.length && previous.length === next.length) {
    return {
      mode: 'noop',
      changedFromIndex,
      changedPoints: [],
    }
  }

  if (changedFromIndex === next.length) {
    changedFromIndex = previous.length
  }

  if (changedFromIndex < previous.length - 1) {
    return {
      mode: 'full',
      changedFromIndex: 0,
      changedPoints: next,
    }
  }

  return {
    mode: 'incremental',
    changedFromIndex,
    changedPoints: next.slice(changedFromIndex),
  }
}

export const toCandlestickPoint = (data: KLineData): CandlestickData => ({
  time: data.time as Time,
  open: data.open,
  high: data.high,
  low: data.low,
  close: data.close,
})

export const toLinePoint = (data: KLineData): LineData => ({
  time: data.time as Time,
  value: data.close,
})

export const toVolumePoint = (data: KLineData): HistogramData => ({
  time: data.time as Time,
  value: data.volume,
  color: data.close >= data.open ? '#26a69a' : '#ef5350',
})
