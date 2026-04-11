import type { KlinePoint } from 'src/model/db/model'

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)

export const isCompatibleKlinePoint = (
  point: Partial<KlinePoint> | undefined | null,
): point is KlinePoint => {
  if (!point) return false

  return (
    typeof point.token0 === 'string' &&
    typeof point.token1 === 'string' &&
    isFiniteNumber(point.poolId) &&
    typeof point.poolApplication === 'string' &&
    typeof point.interval === 'string' &&
    isFiniteNumber(point.timestamp) &&
    isFiniteNumber(point.open) &&
    isFiniteNumber(point.high) &&
    isFiniteNumber(point.low) &&
    isFiniteNumber(point.close) &&
    isFiniteNumber(point.base_volume) &&
    isFiniteNumber(point.quote_volume) &&
    isFiniteNumber(point.bucket_start_ms) &&
    isFiniteNumber(point.bucket_end_ms) &&
    typeof point.is_final === 'boolean'
  )
}

export const splitCompatibleKlinePoints = <T extends Partial<KlinePoint>>(
  points: T[],
): {
  compatible: KlinePoint[]
  incompatible: T[]
} => {
  const compatible: KlinePoint[] = []
  const incompatible: T[] = []

  points.forEach((point) => {
    if (isCompatibleKlinePoint(point)) {
      compatible.push(point)
      return
    }

    incompatible.push(point)
  })

  return {
    compatible,
    incompatible,
  }
}
