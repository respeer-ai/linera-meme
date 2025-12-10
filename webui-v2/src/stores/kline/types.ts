/* eslint-disable camelcase */
import { TransactionExt } from '../transaction'

export interface Point {
  open: number
  high: number
  low: number
  close: number
  volume: number
  timestamp: number
}

export interface Points {
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
