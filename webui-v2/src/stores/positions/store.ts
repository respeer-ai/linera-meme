import axios from 'axios'
import { defineStore } from 'pinia'
import { constants } from 'src/constant'
import { NotifyType } from 'src/stores/notify'
import { Notify } from 'src/stores/notify/wrapper'
import { type Position, type PositionStatusFilter, type PositionsResponse } from './types'

export const usePositionsStore = defineStore('positions', {
  state: () => ({
    owner: '' as string,
    status: 'active' as PositionStatusFilter,
    positions: [] as Position[],
    loading: false,
    loaded: false,
    error: '' as string,
    requestSerial: 0,
  }),
  getters: {
    hasPositions: (state) => state.positions.length > 0,
    activeLiquidityShare: (state) => {
      const total = state.positions.reduce((sum, position) => {
        if (position.status !== 'active') return sum
        return sum + Number.parseFloat(position.current_liquidity || '0')
      }, 0)
      return Number.isFinite(total) ? total : 0
    },
  },
  actions: {
    clear() {
      this.owner = ''
      this.positions = []
      this.loading = false
      this.loaded = false
      this.error = ''
      this.status = 'active'
    },
    async fetchPositions(owner: string, status: PositionStatusFilter = 'active') {
      if (!owner) {
        this.clear()
        return
      }

      const requestSerial = ++this.requestSerial
      this.loading = true
      this.error = ''

      try {
        const url = constants.formalizeSchema(`${constants.KLINE_HTTP_URL}/positions`)
        const response = await axios.get<PositionsResponse>(url, {
          params: { owner, status },
        })

        if (requestSerial !== this.requestSerial) return

        this.owner = response.data.owner
        this.status = status
        this.positions = response.data.positions
        this.loaded = true
      } catch (error) {
        if (requestSerial !== this.requestSerial) return

        console.log('Failed get positions', error)
        const description = error instanceof Error ? error.message : ''
        Notify.pushNotification({
          Title: 'Load positions',
          Message: 'Failed to load positions',
          ...(description ? { Description: description } : {}),
          Popup: true,
          Type: NotifyType.Error,
        })
        this.owner = owner
        this.status = status
        this.positions = []
        this.loaded = true
        this.error = error instanceof Error ? error.message : 'Failed to load positions'
      } finally {
        if (requestSerial === this.requestSerial) {
          this.loading = false
        }
      }
    },
  },
})

export * from './types'
