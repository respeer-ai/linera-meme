import { Account } from '../account'
import { BaseRequest } from '../request'

export type LatestTransactionsRequest = BaseRequest

export interface CreatePoolRequest extends BaseRequest {
  token0: string
  token1?: string
  amount0: string
  amount1: string
  to?: Account
}
