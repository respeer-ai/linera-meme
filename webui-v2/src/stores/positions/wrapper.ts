import { usePositionsStore } from './store'
import { type PositionStatusFilter } from './types'

const positions = usePositionsStore()

export class Positions {
  static fetch = async (owner: string, status: PositionStatusFilter = 'active') => {
    await positions.fetchPositions(owner, status)
  }

  static clear = () => positions.clear()

  static owner = () => positions.owner
  static status = () => positions.status
  static list = () => positions.positions
  static loading = () => positions.loading
  static loaded = () => positions.loaded
  static error = () => positions.error
  static hasPositions = () => positions.hasPositions
  static activeLiquidityShare = () => positions.activeLiquidityShare
}
