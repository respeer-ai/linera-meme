import { BulkError } from 'dexie'
import { dbKline } from 'src/controller'
import { Interval } from 'src/localstore/kline/const'
import { Point } from 'src/localstore/kline/types'
import { dbModel } from 'src/model'

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
          const _point = _points[parseInt(pos.toString())]
          const { timestamp } = _point
          const point = await dbKline.klinePoints.get([
            token0,
            token1,
            interval,
            timestamp
          ])
          if (!point) continue
          _point.id = point.id
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

  static points = async (
    token0: string,
    token1: string,
    interval: Interval,
    offset: number,
    limit: number,
    reverse?: boolean
  ) => {
    return reverse
      ? await dbKline.klinePoints
        .orderBy('timestamp')
        .reverse()
        .filter(
          (obj) =>
            obj.token0 === token0 &&
            obj.token1 === token1 &&
            obj.interval === interval
        )
        .offset(offset)
        .limit(limit)
        .toArray()
      : await dbKline.klinePoints
        .orderBy('timestamp')
        .filter(
          (obj) =>
            obj.token0 === token0 &&
            obj.token1 === token1 &&
            obj.interval === interval
        )
        .offset(offset)
        .limit(limit)
        .toArray()
  }
}
