import Dexie, { type BulkError } from 'dexie'
import { dbKline } from 'src/controller'
import { type Interval } from 'src/stores/kline/const'
import { type Point } from 'src/stores/kline/types'
import { type dbModel } from 'src/model'
import { splitCompatibleKlinePoints } from './klineCacheCompatibility'

export class Kline {
  static bulkPut = async (
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
    interval: Interval,
    points: Point[],
  ) => {
    const _points = points.map((point) => {
      return { ...point, token0, token1, poolId, poolApplication, interval }
    }) as dbModel.KlinePoint[]
    const traceFunc = console.trace
    console.trace = () => {
      // DO NOTHING
    }
    try {
      await dbKline.klinePoints.bulkPut(_points)
    } catch (e) {
      // TODO: update exists item
      const err = e as BulkError
      if (err.name !== 'BulkError') return
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for (const [pos, error] of Object.entries(err.failuresByPos)) {
        try {
          const _point = _points[parseInt(pos.toString())] as dbModel.KlinePoint
          const { timestamp } = _point
          const point = await dbKline.klinePoints.get([
            token0,
            token1,
            poolId,
            poolApplication,
            interval,
            timestamp,
          ])
          if (!point) continue
          _point.id = point.id as number
          if (JSON.stringify(_point) === JSON.stringify(point)) continue
          await dbKline.klinePoints.update(_point, _point)
        } catch (e) {
          // eslint-disable-next-line @typescript-eslint/restrict-template-expressions
          console.log(`Failed update point: ${e}`)
        }
      }
    }
    console.trace = traceFunc
  }

  static timestampRange = async (
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
    interval: Interval,
  ) => {
    const from = [token0, token1, poolId, poolApplication, interval, Dexie.minKey]
    const to = [token0, token1, poolId, poolApplication, interval, Dexie.maxKey]

    const collection = dbKline.klinePoints
      .where('[token0+token1+poolId+poolApplication+interval+timestamp]')
      .between(from, to)

    const minItem = await collection.first()

    return {
      minTimestamp: minItem?.timestamp ?? 0,
      maxTimestamp: Math.floor(Date.now()) + 1 * 3600 * 1000,
    }
  }

  static points = async (
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
    interval: Interval,
    offset?: number,
    limit?: number,
    reverse?: boolean,
    timestampBegin?: number,
    timestampEnd?: number,
  ) => {
    const from = [token0, token1, poolId, poolApplication, interval, timestampBegin ?? 0]
    const to = [token0, token1, poolId, poolApplication, interval, timestampEnd ?? 9999999999999]

    const collection = reverse
      ? dbKline.klinePoints
          .where('[token0+token1+poolId+poolApplication+interval+timestamp]')
          .between(from, to)
          .reverse()
      : dbKline.klinePoints
          .where('[token0+token1+poolId+poolApplication+interval+timestamp]')
          .between(from, to)

    const loadedPoints = await collection
      .offset(offset ?? 0)
      .limit(limit ?? 999999)
      .toArray()

    const { compatible, incompatible } = splitCompatibleKlinePoints(loadedPoints)

    if (incompatible.length > 0) {
      await dbKline.klinePoints.bulkDelete(
        incompatible
          .filter(
            (point) =>
              typeof point.token0 === 'string' &&
              typeof point.token1 === 'string' &&
              typeof point.poolApplication === 'string' &&
              typeof point.poolId === 'number' &&
              typeof point.interval === 'string' &&
              typeof point.timestamp === 'number',
          )
          .map(
            (point) =>
              [
                point.token0,
                point.token1,
                point.poolId,
                point.poolApplication,
                point.interval,
                point.timestamp,
              ] as const,
          ),
      )
    }

    return compatible.sort((a, b) => b.timestamp - a.timestamp)
  }
}
