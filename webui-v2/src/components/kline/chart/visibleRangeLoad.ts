export type VisibleRange = {
  from: number
  to: number
}

export type VisibleRangeLoadDecision = {
  loadOld: boolean
  loadNew: boolean
  loadOrder: Array<'new' | 'old'>
}

type VisibleRangeLoadInput = {
  range: VisibleRange | null
  dataLength: number
}

export const resolveVisibleRangeLoadDecision = ({
  range,
  dataLength,
}: VisibleRangeLoadInput): VisibleRangeLoadDecision => {
  if (!range || dataLength <= 0) {
    return { loadOld: false, loadNew: false, loadOrder: [] }
  }

  const fromIndex = Math.max(Math.floor(range.from), 0)
  const toIndex = Math.min(Math.ceil(range.to), dataLength - 1)

  const reachesStart = fromIndex <= 0
  const reachesEnd = toIndex >= dataLength - 1

  if (reachesStart && reachesEnd) {
    return { loadOld: true, loadNew: true, loadOrder: ['new', 'old'] }
  }

  return {
    loadOld: reachesStart,
    loadNew: reachesEnd,
    loadOrder: reachesStart ? ['old'] : (reachesEnd ? ['new'] : []),
  }
}
