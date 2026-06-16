import {
  type Interval,
  useKlineStore,
  type Point,
  type PositionsInvalidationPayload,
  type TickerInterval,
} from './store'

const kline = useKlineStore()

export class Kline {
  static initialize = () => kline.initializeKline()

  static subscribe = (
    token0: string,
    token1: string,
    interval: Interval,
    poolId: number,
    poolApplication: string,
  ) => kline.subscribeKline(token0, token1, interval, poolId, poolApplication)

  static subscribePositions = (owner: string, poolId?: number, poolApplication?: string) =>
    kline.subscribePositions(owner, poolId, poolApplication)

  static onPositions = (listener: (payload: PositionsInvalidationPayload) => void) =>
    kline.addPositionsListener(listener)

  static latestPoints = (
    key: Interval,
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
  ): Point[] => {
    return kline._latestPoints(key, token0, token1, poolId, poolApplication)
  }

  static pushedTransactions = (token0: string, token1: string, tokenReversed: boolean) => {
    return kline._pushedTransactions(token0, token1, tokenReversed ? 1 : 0)
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

  static poolStat = (
    poolId: number | string,
    interval: TickerInterval,
    poolApplication?: string,
  ) => {
    return kline.poolStat(poolId, interval, poolApplication)
  }

  static getProtocolStat = async () => {
    return await kline.getProtocolStat()
  }

  static getPositionMetrics = async (
    owner: string,
    status: 'active' | 'closed' | 'all' = 'active',
  ) => {
    return await kline.getPositionMetrics(owner, status)
  }

  static getClaimBalances = async (owner: string) => {
    return await kline.getClaimBalances(owner)
  }

  static protocolStat = () => kline.protocolStat
}
