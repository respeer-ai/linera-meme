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

export type LogicalRange = {
  from: number
  to: number
}

const DEFAULT_RENDER_SIGNAL_TAIL_SIZE = 8

const pointsEqual = (left: KLineData, right: KLineData) => (
  left.time === right.time &&
  left.open === right.open &&
  left.high === right.high &&
  left.low === right.low &&
  left.close === right.close &&
  left.volume === right.volume
)

const resolveDataOffset = ({
  previousData,
  nextData,
}: {
  previousData: KLineData[]
  nextData: KLineData[]
}) => {
  if (!previousData.length || nextData.length < previousData.length) return null

  const maxOffset = nextData.length - previousData.length

  for (let offset = 0; offset <= maxOffset; offset += 1) {
    let matches = true

    for (let index = 0; index < previousData.length; index += 1) {
      if (previousData[index]?.time !== nextData[index + offset]?.time) {
        matches = false
        break
      }
    }

    if (matches) return offset
  }

  return null
}

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

export const getChartDataRenderSignal = (
  data: KLineData[],
  tailSize = DEFAULT_RENDER_SIGNAL_TAIL_SIZE,
) => {
  if (!data.length) return '0'

  const firstTime = data[0]?.time ?? 0
  const tail = data.slice(Math.max(data.length - tailSize, 0))
  const tailSignature = tail
    .map((point) => [point.time, point.open, point.high, point.low, point.close, point.volume].join(':'))
    .join('|')

  return `${data.length}#${firstTime}#${tailSignature}`
}

export const resolveVisibleLogicalRangeRestore = ({
  previousData,
  nextData,
  previousRange,
}: {
  previousData: KLineData[]
  nextData: KLineData[]
  previousRange: LogicalRange | null
}): LogicalRange | null => {
  if (!previousRange || !previousData.length) return null

  const dataOffset = resolveDataOffset({
    previousData,
    nextData,
  })

  if (dataOffset === null) return null

  return {
    from: previousRange.from + dataOffset,
    to: previousRange.to + dataOffset,
  }
}

export const shouldScrollToLatestOnFirstRender = ({
  previousData,
  nextData,
  previousRange,
  minimumDataPointsToAnchor = 1,
}: {
  previousData: KLineData[]
  nextData: KLineData[]
  previousRange: LogicalRange | null
  minimumDataPointsToAnchor?: number
}) => (
  !previousData.length &&
  nextData.length >= minimumDataPointsToAnchor &&
  previousRange === null
)

export const shouldFitContentOnFirstRender = ({
  previousData,
  nextData,
  previousRange,
  minimumDataPointsToAnchor = 1,
}: {
  previousData: KLineData[]
  nextData: KLineData[]
  previousRange: LogicalRange | null
  minimumDataPointsToAnchor?: number
}) => (
  !previousData.length &&
  nextData.length > 0 &&
  nextData.length < minimumDataPointsToAnchor &&
  previousRange === null
)

export const resolveVisibleLogicalRangeAfterPrimaryRender = ({
  renderMode,
  previousData,
  nextData,
  previousRange,
}: {
  renderMode: PrimarySeriesRenderPlan['mode']
  previousData: KLineData[]
  nextData: KLineData[]
  previousRange: LogicalRange | null
}) => {
  if (renderMode !== 'full') return null

  return resolveVisibleLogicalRangeRestore({
    previousData,
    nextData,
    previousRange,
  })
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
