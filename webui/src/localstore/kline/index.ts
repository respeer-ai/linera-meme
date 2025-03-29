import { defineStore } from 'pinia'
import { Points, Point, GetKlineRequest, GetTransactionsRequest } from './types'
import { _WebSocket } from './websocket'
import { constants } from 'src/constant'
import { doGetWithError } from '../request'
import { TransactionExt } from '../transaction'

export const useKlineStore = defineStore('kline', {
  state: () => ({
    points: new Map<string, Map<string, Point[]>>(),
    websocket: undefined as unknown as _WebSocket,
    latestPoints: new Map<string, Points[]>(),
    transactions: new Map<string, TransactionExt[]>()
  }),
  actions: {
    initializeKline () {
      this.websocket = new _WebSocket(constants.KLINE_WS_URL)
      this.websocket.withOnMessage(this.onMessage)
      this.websocket.withOnError(this.onError)
    },
    onMessage (points: Map<string, Points[]>) {
      this.latestPoints = points
      points.forEach((_points, key) => {
        const __points = this.points.get(key) || new Map<string, Point[]>()
        _points.forEach((points) => {
          const ___points = __points.get(`${points.token_0}:${points.token_1}`) || []
          points.points.forEach((point) => {
            point.timestamp = Math.floor(Date.parse(point.timestamp as unknown as string))
            const index = ___points.findIndex((el) => el.timestamp === point.timestamp)
            ___points.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, point)
          })
          __points.set(`${points.token_0}:${points.token_1}`, ___points)
        })
        this.points.set(key, __points)
      })
    },
    onError (e: Event) {
      console.log(`Kline error: ${JSON.stringify(e)}`)
    },
    getKline (req: GetKlineRequest, done?: (error: boolean, rows?: Map<string, Points[]>) => void) {
      const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/points/token0/${req.token0}/token1/${req.token1}/start_at/${req.startAt}/end_at/${req.endAt}/interval/${req.interval}`)
      doGetWithError(url, req, req.Message, (resp: Points) => {
        const r = new Map<string, Points[]>()
        r.set(req.interval, [resp])
        this.onMessage(r)
        done?.(false)
      }, () => {
        done?.(true)
      })
    },
    getTransactions (req: GetTransactionsRequest, done?: (error: boolean, rows?: Map<string, Points[]>) => void) {
      const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/transactions/token0/${req.token0}/token1/${req.token1}/start_at/${req.startAt}/end_at/${req.endAt}`)
      doGetWithError(url, req, req.Message, (resp: TransactionExt[]) => {
        this.appendTransactions(req.token0, req.token1, resp)
        done?.(false)
      }, () => {
        done?.(true)
      })
    },
    appendTransactions (token0: string, token1: string, transactions: TransactionExt[]) {
      const _transactions = this.transactions.get(`${token0}:${token1}`) || []
      transactions.forEach((transaction) => {
        const index = _transactions.findIndex((el) => el.transaction_id === transaction.transaction_id)
        _transactions.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, transaction)
      })
      this.transactions.set(`${token0}:${token1}`, _transactions)
    }
  },
  getters: {
    _points (): (key: string, token_0: string, token_1: string) => Point[] {
      return (key: string, token_0: string, token_1: string) => {
        return ((this.points.get(key) || new Map<string, Point[]>()).get(`${token_0}:${token_1}`) || []).sort((a, b) => a.timestamp - b.timestamp)
      }
    },
    _latestPoints (): (key: string, token_0: string, token_1: string) => Point[] {
      return (key: string, token_0: string, token_1: string) => {
        return ((this.latestPoints.get(key) || []).find((el) => el.token_0 === token_0 && el.token_1 === token_1)?.points || []).sort((a, b) => a.timestamp - b.timestamp)
      }
    },
    _transactions (): (token0: string, token1: string) => TransactionExt[] {
      return (token0: string, token1: string) => {
        return (this.transactions.get(`${token0}:${token1}`) || []).sort((a, b) => a.created_at - b.created_at)
      }
    }
  }
})

export * from './types'
export * from './const'
