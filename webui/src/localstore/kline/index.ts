import { defineStore } from 'pinia'
import { Points, Point } from './types'
import { _WebSocket } from './websocket'
import { constants } from 'src/constant'

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
            const index = ___points.findIndex((el) => el.timestamp === point.timestamp)
            point.timestamp = Math.floor(point.timestamp)
            ___points.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, point)
          })
          __points.set(`${points.token_0}:${points.token_1}`, ___points)
        })
        this.points.set(key, __points)
      })
    },
    onError (e: Event) {
      console.log(`Kline error: ${JSON.stringify(e)}`)
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
