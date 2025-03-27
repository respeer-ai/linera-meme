import { Account } from '../account'
import { BaseRequest } from '../request'

export type LatestTransactionsRequest = BaseRequest

export enum TransactionType {
  ADD_LIQUIDITY = 'AddLiquidity',
  REMOVE_LIQUIDITY = 'RemoveLiquidity',
  BUY_TOKEN0 = 'BuyToken0',
  SELL_TOKEN0 = 'SellToken0'
}

export interface Transaction {
  transactionType: TransactionType
  from: Account
  amount0In?: string
  amount1In?: string
  amount0Out?: string
  amount1Out?: string
  liquidity?: string
  createdAt: number
}
