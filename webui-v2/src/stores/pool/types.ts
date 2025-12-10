import { type BaseRequest } from '../request'

export interface LatestTransactionsRequest extends BaseRequest {
  startId?: number
}

export interface LiquidityAmount {
  liquidity: string
  amount0: string
  amount1: string
}

export interface CalculateLiquidityAmountPairRequest extends BaseRequest {
  amount0Desired?: string
  amount1Desired?: string
}

export interface LiquidityRequest extends BaseRequest {
  owner: string
}
