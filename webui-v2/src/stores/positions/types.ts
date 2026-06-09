export type PositionStatus = 'active' | 'closed' | 'virtual'
export type PositionStatusFilter = 'active' | 'closed' | 'all'

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
  position_kind?: string | null
  is_virtual_position?: boolean | null
  virtual_initial_amount0?: string | null
  virtual_initial_amount1?: string | null
  protocol_fee_receiver_account?: string | null
  protocol_fee_reference_amount0?: string | null
  protocol_fee_reference_amount1?: string | null
  virtual_current_liquidity?: string | null
}

export interface PositionsResponse {
  owner: string
  positions: Position[]
}
