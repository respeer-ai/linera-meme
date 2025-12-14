import { type Interval, useKlineStore, type Point } from './store'

const kline = useKlineStore()

export class Kline {
  static initialize = () => kline.initializeKline()

  static latestPoints = (key: Interval, token0: string, token1: string): Point[] => {
    return kline._latestPoints(key, token0, token1)
  }
}
