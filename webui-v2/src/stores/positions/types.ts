export type PositionStatus = 'active' | 'closed'
export type PositionStatusFilter = PositionStatus | 'all'

export interface Position {
  pool_application: string
  pool_id: number
  token_0: string
  token_1: string
  owner: string
  status: PositionStatus
  current_liquidity: string
  added_liquidity: string
  removed_liquidity: string
  add_tx_count: number
  remove_tx_count: number
  opened_at: number | null
  updated_at: number | null
  closed_at: number | null
}

export interface PositionsResponse {
  owner: string
  positions: Position[]
}
