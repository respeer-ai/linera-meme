import { dbKline } from 'src/controller'
import { Interval } from 'src/localstore/kline/const'
import { Point } from 'src/localstore/kline/types'

export class Kline {
  static bulkPut = async (
    token0: string,
    token1: string,
    interval: Interval,
    points: Point[]
  ) => {
    const _points = points.map((point) => {
      return { ...point, token0, token1, interval }
    })
    const traceFunc = console.trace
    console.trace = () => {
      // DO NOTHING
    }
    try {
      await dbKline.klinePoints.bulkPut(_points)
    } catch {
      // DO NOTHING
    }
    console.trace = traceFunc
  }

  static points = async (
    token0: string,
    token1: string,
    interval: Interval,
    offset: number,
    limit: number
  ) => {
    return await dbKline.klinePoints
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
