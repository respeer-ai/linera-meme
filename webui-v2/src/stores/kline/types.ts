import { type TransactionExt } from '../transaction'
import { type TickerInterval } from './const'

export interface Point {
  id?: number
  bucket_start_ms?: number
  bucket_end_ms?: number
  is_final?: boolean
  open: number
  high: number
  low: number
  close: number
  base_volume: number
  quote_volume: number
  timestamp: number
}

export interface Points {
  pool_id?: number
  pool_application?: string
  token_0: string
  token_1: string
  start_at: number
  end_at: number
  interval: string
  points: Point[]
}

export interface Transactions {
  token_0: string
  token_1: string
  transactions: Array<TransactionExt>
}

export interface KlineInformation {
  count: number
  timestamp_begin: number
  timestamp_end: number
}

export interface TransactionsInformation {
  count: number
  timestamp_begin: number
  timestamp_end: number
}

export interface TickerStat {
  token: string
  high: string
  low: string
  volume: string
  tx_count: number
  price_now: string
  price_start: string
}

export interface Tickers {
  interval: TickerInterval
  stats: TickerStat[]
}

export interface PoolStat {
  pool_id: number
  token_0: string
  token_1: string
  high: string
  low: string
  volume: string
  tx_count: number
  price_now: string
  price_start: string
}

export interface PoolStats {
  interval: TickerInterval
  stats: PoolStat[]
}

export interface ProtocolStat {
  tvl: string
  tvl_change: number
  volume: string
  volume_change: number
  fees: number
  tx_count: number
  pool_count: number
}

export type PositionMetricsStatus =
  | 'partial_live_redeemable_only'
  | 'exact_no_swap_history'
  | 'exact_swap_history_no_post_open_liquidity_changes'

export type PositionMetricsBlocker =
  | 'missing_liquidity_history'
  | 'missing_live_liquidity'
  | 'liquidity_history_mismatch'
  | 'virtual_initial_liquidity_present'
  | 'pool_has_swap_history_after_position_open'
  | 'uniswap_v2_fee_split_not_supported_yet'
  | 'missing_live_redeemable_amounts'

export interface PositionMetricsEntry {
  pool_application: string
  pool_id: number
  token_0: string
  token_1: string
  owner: string
  status: 'active' | 'closed'
  current_liquidity: string
  position_liquidity_live: string | null
  total_supply_live: string | null
  exact_share_ratio: string | null
  redeemable_amount0: string | null
  redeemable_amount1: string | null
  virtual_initial_liquidity: boolean
  metrics_status: PositionMetricsStatus
  exact_fee_supported: boolean
  exact_principal_supported: boolean
  owner_is_fee_to: boolean
  computation_blockers: PositionMetricsBlocker[]
  principal_amount0: string | null
  principal_amount1: string | null
  fee_amount0: string | null
  fee_amount1: string | null
  protocol_fee_amount0: string | null
  protocol_fee_amount1: string | null
}

export interface PositionMetricsResponse {
  owner: string
  metrics: PositionMetricsEntry[]
}
