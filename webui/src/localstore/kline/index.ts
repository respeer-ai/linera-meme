import { defineStore } from 'pinia'
import {
  Points,
  Point,
  GetKlineRequest,
  GetTransactionsRequest,
  Notification,
  Transactions,
  TimestampPoints
} from './types'
import { _WebSocket } from './websocket'
import { constants } from 'src/constant'
import { doGetWithError } from '../request'
import { TransactionExt } from '../transaction'

export const useKlineStore = defineStore('kline', {
  state: () => ({
    points: new Map<string, Map<string, TimestampPoints>>(),
    latestTimestamps: new Map<string, Map<string, number>>(),
    websocket: undefined as unknown as _WebSocket,
    latestPoints: new Map<string, Points[]>(),
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
            Object.entries(notification.value as Record<string, Points[]>)
          )
        )
      } else if (notification.notification === 'transactions') {
        this.onTransactions(notification.value as Transactions[])
      }
    },
    onKline(points: Map<string, Points[]>) {
      points.forEach((_points, key) => {
        const __points =
          this.points.get(key) || new Map<string, TimestampPoints>()
        _points.forEach((points) => {
          const ___points = __points.get(
            `${points.token_0}:${points.token_1}`
          ) || {
            points: [],
            latestTimestamp: 0
          }
          points.points.forEach((point) => {
            point.timestamp = Math.floor(
              Date.parse(point.timestamp as unknown as string)
            )
            const index = ___points.points.findIndex(
              (el) => el.timestamp === point.timestamp
            )
            if (index >= 0) {
              ___points[index] = point
              return
            }
            ___points.points.push(point)
            ___points.latestTimestamp = Math.max(
              point.timestamp,
              ___points.latestTimestamp
            )
          })
          __points.set(`${points.token_0}:${points.token_1}`, ___points)
        })
        this.points.set(key, __points)
      })
      this.latestPoints = points
    },
    onError(e: Event) {
      console.log(`Kline error: ${JSON.stringify(e)}`)
    },
    getKline(
      req: GetKlineRequest,
      done?: (error: boolean, rows?: Map<string, Points[]>) => void
    ) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/points/token0/${req.token0}/token1/${req.token1}/start_at/${req.startAt}/end_at/${req.endAt}/interval/${req.interval}`
      )
      doGetWithError(
        url,
        req,
        req.Message,
        (resp: Points) => {
          const r = new Map<string, Points[]>()
          r.set(req.interval, [resp])
          this.onKline(r)
          done?.(false)
        },
        () => {
          done?.(true)
        }
      )
    },
    getTransactions(
      req: GetTransactionsRequest,
      done?: (error: boolean, rows?: TransactionExt[]) => void
    ) {
      const url = constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/transactions/token0/${req.token0}/token1/${req.token1}/start_at/${req.startAt}/end_at/${req.endAt}`
      )
      doGetWithError(
        url,
        req,
        req.Message,
        (resp: TransactionExt[]) => {
          this.appendTransactions(req.token0, req.token1, resp)
          done?.(false, resp)
        },
        () => {
          done?.(true)
        }
      )
    },
    onTransactions(transactions: Transactions[]) {
      transactions.forEach((_transactions) => {
        this.appendTransactions(
          _transactions.token_0,
          _transactions.token_1,
          _transactions.transactions
        )
      })
    },
    appendTransactions(
      token0: string,
      token1: string,
      transactions: TransactionExt[]
    ) {
      transactions.forEach((transaction) => {
        const _token0 = transaction.token_reversed ? token1 : token0
        const _token1 = transaction.token_reversed ? token0 : token1

        const _transactions =
          this.transactions.get(`${_token0}:${_token1}`) || []
        const index = _transactions.findIndex(
          (el) => el.transaction_id === transaction.transaction_id
        )
        _transactions.splice(
          index >= 0 ? index : 0,
          index >= 0 ? 1 : 0,
          transaction
        )
        this.transactions.set(`${_token0}:${_token1}`, _transactions)
      })
    }
  },
  getters: {
    _points(): (key: string, token0: string, token1: string) => Point[] {
      return (key: string, token0: string, token1: string) => {
        return (
          (this.points.get(key) || new Map<string, TimestampPoints>()).get(
            `${token0}:${token1}`
          ) || {
            points: [],
            latestTimestamp: 0
          }
        ).points.sort((a, b) => a.timestamp - b.timestamp)
      }
    },
    latestTimestamp(): (key: string, token0: string, token1: string) => number {
      return (key: string, token0: string, token1: string) => {
        return (
          (this.points.get(key) || new Map<string, TimestampPoints>()).get(
            `${token0}:${token1}`
          ) || {
            points: [],
            latestTimestamp: 0
          }
        ).latestTimestamp
      }
    },
    _latestPoints(): (key: string, token0: string, token1: string) => Point[] {
      return (key: string, token0: string, token1: string) => {
        return (
          (this.latestPoints.get(key) || []).find(
            (el) => el.token_0 === token0 && el.token_1 === token1
          )?.points || []
        ).sort((a, b) => a.timestamp - b.timestamp)
      }
    },
    _transactions(): (token0: string, token1: string) => TransactionExt[] {
      return (token0: string, token1: string) => {
        return (this.transactions.get(`${token0}:${token1}`) || []).sort(
          (a, b) => a.created_at - b.created_at
        )
      }
    }
  }
})

export * from './types'
export * from './const'
