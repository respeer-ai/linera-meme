import { defineStore } from 'pinia'
import { Points, Point, GetKlineRequest } from './types'
import { _WebSocket } from './websocket'
import { constants } from 'src/constant'
import { doGetWithError } from '../request'

export const useKlineStore = defineStore('kline', {
  state: () => ({
    points: new Map<string, Map<string, Point[]>>(),
    websocket: undefined as unknown as _WebSocket,
    latestPoints: new Map<string, Points[]>()
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
      const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/kline/token0/${req.token0}/token1/${req.token1}/start_at/${req.startAt}/end_at/${req.endAt}/interval/${req.interval}`)
      doGetWithError(url, req, req.Message, (resp: Points) => {
        const r = new Map<string, Points[]>()
        r.set(req.interval, [resp])
        this.onMessage(r)
        done?.(false)
      }, () => {
        done?.(true)
      })
    }
  },
  getters: {
    _points (): (key: string, token_0: string, token_1: string) => Point[] {
      return (key: string, token_0: string, token_1: string) => {
        return (this.points.get(key) || new Map<string, Point[]>()).get(`${token_0}:${token_1}`) || []
      }
    }
  }
})

export * from './types'
