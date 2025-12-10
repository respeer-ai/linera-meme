import Dexie, { type BulkError } from 'dexie'
import { dbKline } from 'src/controller'
import { type Interval } from 'src/stores/kline/const'
import { type Point } from 'src/stores/kline/types'
import { type dbModel } from 'src/model'
import { type KlinePoint } from 'src/model/db/model'

export class Kline {
  static bulkPut = async (
    token0: string,
    token1: string,
    interval: Interval,
    points: Point[]
  ) => {
    const _points = points.map((point) => {
      return { ...point, token0, token1, interval }
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
          const _point = _points[parseInt(pos.toString())] as Point
          const { timestamp } = _point
          const point = await dbKline.klinePoints.get([
            token0,
            token1,
            interval,
            timestamp
          ])
          if (!point) continue
          _point.id = point.id as number
          if (JSON.stringify(_point) === JSON.stringify(point)) continue
          await dbKline.klinePoints.update(_point as KlinePoint, _point)
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
    interval: Interval
  ) => {
    const from = [token0, token1, interval, Dexie.minKey]
    const to = [token0, token1, interval, Dexie.maxKey]

    const collection = dbKline.klinePoints
      .where('[token0+token1+interval+timestamp]')
      .between(from, to)

    const minItem = await collection.first()

    return {
      minTimestamp: minItem?.timestamp ?? 0,
      maxTimestamp: Math.floor(Date.now()) + 1 * 3600 * 1000
    }
  }

  static points = async (
    token0: string,
    token1: string,
    interval: Interval,
    offset?: number,
    limit?: number,
    reverse?: boolean,
    timestampBegin?: number,
    timestampEnd?: number
  ) => {
    const from = [token0, token1, interval, timestampBegin ?? 0]
    const to = [token0, token1, interval, timestampEnd ?? 9999999999999]

    const collection = reverse
      ? dbKline.klinePoints
          .where('[token0+token1+interval+timestamp]')
          .between(from, to)
          .reverse()
      : dbKline.klinePoints
          .where('[token0+token1+interval+timestamp]')
          .between(from, to)

    return (
      await collection
        .offset(offset ?? 0)
        .limit(limit ?? 999999)
        .toArray()
    ).sort((a, b) => b.timestamp - a.timestamp)
  }
}
