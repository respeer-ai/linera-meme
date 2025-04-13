import { defineStore } from 'pinia'
import { Points, Point, Notification, Transactions } from './types'
import { _WebSocket } from './websocket'
import { constants } from 'src/constant'
import { TransactionExt } from '../transaction'
import { klineWorker } from 'src/worker'
import { Interval } from './const'

export const useKlineStore = defineStore('kline', {
  state: () => ({
    latestTimestamps: new Map<string, Map<string, Map<Interval, number>>>(),
    websocket: undefined as unknown as _WebSocket,
    latestPoints: new Map<Interval, Points[]>(),
    transactions: new Map<string, TransactionExt[]>()
  }),
  actions: {
    initializeKline() {
      this.websocket = new _WebSocket(constants.KLINE_WS_URL)
      this.websocket.withOnMessage((notification) =>
        this.onMessage(notification)
      )
      this.websocket.withOnError((e) => this.onError(e))
    },
    onMessage(notification: Notification) {
      if (notification.notification === 'kline') {
        this.onKline(
          new Map(
            Object.entries(notification.value as Record<Interval, Points[]>)
          ) as Map<Interval, Points[]>
        )
      } else if (notification.notification === 'transactions') {
        this.onTransactions(notification.value as Transactions[])
      }
    },
    onKline(points: Map<Interval, Points[]>) {
      klineWorker.KlineWorker.send(
        klineWorker.KlineEventType.NEW_POINTS,
        points
      )
      points.forEach((_points, interval) => {
        _points.forEach((__points) => {
          const _latestTimestamps =
            this.latestTimestamps.get(__points.token_0) ||
            new Map<string, Map<Interval, number>>()
          const __latestTimestamps =
            _latestTimestamps.get(__points.token_1) ||
            new Map<Interval, number>()

          __points.points = __points.points.map((el) => {
            return {
              ...el,
              timestamp: Math.floor(
                Date.parse(el.timestamp as unknown as string)
              )
            }
          })

          __latestTimestamps.set(
            interval,
            Math.max(
              ...__points.points.map((el) =>
                Math.floor(Date.parse(el.timestamp as unknown as string))
              )
            )
          )
          _latestTimestamps.set(__points.token_1, __latestTimestamps)
          this.latestTimestamps.set(__points.token_0, _latestTimestamps)
        })
      })
      this.latestPoints = points
    },
    onError(e: Event) {
      console.log(`Kline error: ${JSON.stringify(e)}`)
    },
    onTransactions(transactions: Transactions[]) {
      klineWorker.KlineWorker.send(
        klineWorker.KlineEventType.NEW_TRANSACTIONS,
        transactions
      )
    }
  },
  getters: {
    latestTimestamp(): (
      key: Interval,
      token0: string,
      token1: string
    ) => number {
      return (key: Interval, token0: string, token1: string) => {
        return (
          (
            (
              this.latestTimestamps.get(token0) ||
              new Map<string, Map<Interval, number>>()
            ).get(token1) || new Map<Interval, number>()
          ).get(key) || 0
        )
      }
    },
    _latestPoints(): (
      key: Interval,
      token0: string,
      token1: string
    ) => Point[] {
      return (key: Interval, token0: string, token1: string) => {
        return (
          (this.latestPoints.get(key) || []).find(
            (el) => el.token_0 === token0 && el.token_1 === token1
          )?.points || []
        ).sort((a, b) => a.timestamp - b.timestamp)
      }
    }
  }
})

export * from './types'
export * from './const'
