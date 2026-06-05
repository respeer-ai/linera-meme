import { type Point } from './types'

const isFinal = (point: Point) => point.is_final === true

const volumeValue = (point: Point) => point.base_volume

export const shouldOverwriteOverlappingPoint = (current: Point, incoming: Point): boolean => {
  if (isFinal(current) && !isFinal(incoming)) return false
  if (volumeValue(current) > 0 && volumeValue(incoming) === 0) return false
  return true
}
