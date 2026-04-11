import type { Interval } from './const'
import type { Point, Points } from './types'
import { shouldOverwriteOverlappingPoint } from 'src/worker/kline/pointMerge'

const mergePointLists = (current: Point[], incoming: Point[]): Point[] => {
  const merged = new Map<number, Point>()

  current.forEach((point) => merged.set(point.timestamp, point))
  incoming.forEach((point) => {
    const existing = merged.get(point.timestamp)
    if (!existing || shouldOverwriteOverlappingPoint(existing, point)) {
      merged.set(point.timestamp, point)
    }
  })

  return [...merged.values()].sort((left, right) => left.timestamp - right.timestamp)
}

const mergePointsEntry = (current: Points | undefined, incoming: Points): Points => {
  const points = mergePointLists(current?.points || [], incoming.points)

  return {
    ...(incoming.pool_id !== undefined ? { pool_id: incoming.pool_id } : {}),
    ...(incoming.pool_application !== undefined
      ? { pool_application: incoming.pool_application }
      : {}),
    token_0: incoming.token_0,
    token_1: incoming.token_1,
    interval: incoming.interval,
    start_at: points[0]?.timestamp || incoming.start_at,
    end_at: points[points.length - 1]?.timestamp || incoming.end_at,
    points,
  }
}

export const mergeLatestPointMaps = (
  current: Map<Interval, Points[]>,
  incoming: Map<Interval, Points[]>,
): Map<Interval, Points[]> => {
  const merged = new Map(current)

  incoming.forEach((incomingEntries, interval) => {
    const existingEntries = merged.get(interval) || []
    const mergedEntries = new Map(
      existingEntries.map((entry) => [
        `${entry.token_0}:${entry.token_1}:${entry.pool_id ?? 'none'}:${entry.pool_application ?? 'none'}`,
        entry,
      ]),
    )

    incomingEntries.forEach((entry) => {
      const key = `${entry.token_0}:${entry.token_1}:${entry.pool_id ?? 'none'}:${entry.pool_application ?? 'none'}`
      mergedEntries.set(key, mergePointsEntry(mergedEntries.get(key), entry))
    })

    merged.set(interval, [...mergedEntries.values()])
  })

  return merged
}

export const buildKlineSubscriptionMessage = (
  token_0: string,
  token_1: string,
  interval: Interval,
  pool_id?: number,
  pool_application?: string,
) => ({
  action: 'subscribe',
  topic: 'kline',
  token_0,
  token_1,
  pool_id,
  pool_application,
  intervals: [interval],
})
