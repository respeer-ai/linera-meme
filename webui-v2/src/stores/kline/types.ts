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
