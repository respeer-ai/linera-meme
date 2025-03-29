import { BaseRequest } from '../request'

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

export interface Notification {
  notification: string
  value: Map<string, Points[]>
}

export interface GetKlineRequest extends BaseRequest {
  token0: string
  token1: string
  startAt: number
  endAt: number
  interval: string
}

export interface GetTransactionsRequest extends BaseRequest {
  token0: string
  token1: string
  startAt: number
  endAt: number
}
