import { type Account } from '../account'
import { type BaseRequest } from '../request'

export type LatestTransactionsRequest = BaseRequest

export interface CreatePoolRequest extends BaseRequest {
  token0: string
  token1?: string
  amount0: string
  amount1: string
  to?: Account
}
