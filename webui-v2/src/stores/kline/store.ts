import { defineStore } from 'pinia'
import {
  type Points,
  type Point,
  type Transactions,
  type KlineInformation,
  type TransactionsInformation,
  type Tickers,
  type TickerStat,
  type PoolStats,
  type PoolStat,
  type ProtocolStat,
} from './types'
import { _WebSocket, type Notification } from 'src/websocket'
import { constants } from 'src/constant'
import { type TransactionExt } from '../transaction'
import { klineWorker } from 'src/worker'
import { type TickerInterval, type Interval } from './const'
import axios from 'axios'

export const useKlineStore = defineStore('kline', {
  state: () => ({
    latestTimestamps: new Map<string, Map<string, Map<Interval, number>>>(),
    websocket: undefined as unknown as _WebSocket,
    latestPoints: new Map<Interval, Points[]>(),
    latestTransactions: new Map<string, Map<string, TransactionExt[]>>(),
    tickers: new Map<TickerInterval, Map<string, TickerStat>>(),
    poolStats: new Map<TickerInterval, Map<number, PoolStat>>(),
    protocolStat: {} as ProtocolStat
  }),
  actions: {
    initializeKline() {
      this.websocket = new _WebSocket(constants.KLINE_WS_URL)
      this.websocket.withOnMessage((notification) => this.onMessage(notification))
      this.websocket.withOnError((e) => this.onError(e))
    },
    onMessage(notification: Notification) {
      if (notification.notification === 'kline') {
        this.onKline(
          new Map(Object.entries(notification.value as Record<Interval, Points[]>)) as Map<
            Interval,
            Points[]
          >,
        )
      } else if (notification.notification === 'transactions') {
        this.onTransactions(notification.value as Transactions[])
      }
    },
    onKline(points: Map<Interval, Points[]>) {
      points.forEach((_points, interval) => {
        _points.forEach((__points) => {
          const _latestTimestamps =
            this.latestTimestamps.get(__points.token_0) || new Map<string, Map<Interval, number>>()
          const __latestTimestamps =
            _latestTimestamps.get(__points.token_1) || new Map<Interval, number>()

          __latestTimestamps.set(interval, Math.max(...__points.points.map((el) => el.timestamp)))
          _latestTimestamps.set(__points.token_1, __latestTimestamps)
          this.latestTimestamps.set(__points.token_0, _latestTimestamps)
        })
      })
      klineWorker.KlineWorker.send(klineWorker.KlineEventType.NEW_POINTS, points)
      this.latestPoints = points
    },
    onError(e: Event) {
      console.log(`Kline error: ${JSON.stringify(e)}`)
    },
    onTransactions(transactions: Transactions[]) {
      klineWorker.KlineWorker.send(klineWorker.KlineEventType.NEW_TRANSACTIONS, transactions)
      transactions.forEach((_transactions) => {
        const trans =
          this.latestTransactions.get(_transactions.token_0) || new Map<string, TransactionExt[]>()
        trans.set(_transactions.token_1, _transactions.transactions)
        this.latestTransactions.set(_transactions.token_0, trans)
      })
    },
    async getKlineInformation(token0: string, token1: string, interval: Interval) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/points/token0/${token0}/token1/${token1}/interval/${interval}/information`,
      )
      try {
        const res = await axios.get(url)
        return res.data as KlineInformation
      } catch (e) {
        console.log('Failed get kline information', e)
      }
    },
    async getTransactionsInformation(token0: string, token1: string) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/transactions/token0/${token0}/token1/${token1}/information`,
      )
      try {
        const res = await axios.get(url)
        return res.data as TransactionsInformation
      } catch (e) {
        console.log('Failed get transactions information', e)
      }
    },
    async getCombinedTransactionsInformation() {
      const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/transactions/information`)
      try {
        const res = await axios.get(url)
        return res.data as TransactionsInformation
      } catch (e) {
        console.log('Failed get transactions information', e)
      }
    },
    async getTickers(interval: TickerInterval) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/ticker/interval/${interval}`,
      )
      try {
        const res = await axios.get(url)
        this.tickers.set(
          interval,
          new Map<string, TickerStat>((res.data as Tickers).stats.map((s) => [s.token, s])),
        )
        return res.data as Tickers
      } catch (e) {
        console.log('Failed get tickers', e)
      }
    },
    async getPoolStats(interval: TickerInterval) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/poolstats/interval/${interval}`,
      )
      try {
        const res = await axios.get(url)
        this.poolStats.set(
          interval,
          new Map<number, PoolStat>((res.data as PoolStats).stats.map((s) => [s.pool_id, s])),
        )
        return res.data as PoolStats
      } catch (e) {
        console.log('Failed get tickers', e)
      }
    },
    async getProtocolStat() {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/protocol/stats`,
      )
      try {
        const res = await axios.get(url)
        this.protocolStat = res.data as ProtocolStat
        return res.data as ProtocolStat
      } catch (e) {
        console.log('Failed get protocol stats', e)
      }
    },
  },
  getters: {
    latestTimestamp(): (key: Interval, token0: string, token1: string) => number {
      return (key: Interval, token0: string, token1: string) => {
        return this.latestTimestamps.get(token0)?.get(token1)?.get(key) || 0
      }
    },
    _latestPoints(): (key: Interval, token0: string, token1: string) => Point[] {
      return (key: Interval, token0: string, token1: string) => {
        return (
          (this.latestPoints.get(key) || []).find(
            (el) => el.token_0 === token0 && el.token_1 === token1,
          )?.points || []
        ).sort((a, b) => a.timestamp - b.timestamp)
      }
    },
    _latestTransactions(): (
      token0: string,
      token1: string,
      tokenReversed: number,
    ) => TransactionExt[] {
      return (token0: string, token1: string, tokenReversed: number) => {
        return (
          this.latestTransactions
            .get(token0)
            ?.get(token1)
            ?.sort((a, b) => a.created_at - b.created_at)
            ?.filter((el) => el.token_reversed === tokenReversed) || []
        )
      }
    },
    tokenStat(): (token: string, interval: TickerInterval) => TickerStat | undefined {
      return (token: string, interval: TickerInterval) => {
        return this.tickers.get(interval)?.get(token)
      }
    },
    poolStat(): (poolId: number, interval: TickerInterval) => PoolStat | undefined {
      return (poolId: number, interval: TickerInterval) => {
        console.log(poolId, interval, this.poolStats)
        return this.poolStats.get(interval)?.get(poolId)
      }
    },
  },
})

export * from './types'
export * from './const'
