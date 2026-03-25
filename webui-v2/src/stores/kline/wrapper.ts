import { type Interval, useKlineStore, type Point, type TickerInterval } from './store'

const kline = useKlineStore()

export class Kline {
  static initialize = () => kline.initializeKline()

  static latestPoints = (key: Interval, token0: string, token1: string): Point[] => {
    return kline._latestPoints(key, token0, token1)
  }

  static latestTransactions = (token0: string, token1: string, tokenReversed: boolean) => {
    return kline._latestTransactions(token0, token1, tokenReversed ? 1 : 0)
  }

  static getTransactionsInformation = async (token0?: string, token1?: string) => {
    return token0 && token1
      ? await kline.getTransactionsInformation(token0, token1)
      : await kline.getCombinedTransactionsInformation()
  }

  static getTickers = async (interval: TickerInterval) => {
    return await kline.getTickers(interval)
  }

  static getPoolStats = async (interval: TickerInterval) => {
    return await kline.getPoolStats(interval)
  }

  static tokenStat = (tokenId: string, interval: TickerInterval) => {
    return kline.tokenStat(tokenId, interval)
  }

  static poolStat = (poolId: number, interval: TickerInterval) => {
    return kline.poolStat(poolId, interval)
  }
}
