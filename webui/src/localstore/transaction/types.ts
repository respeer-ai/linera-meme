import { Account } from '../account'

export enum TransactionType {
  ADD_LIQUIDITY = 'AddLiquidity',
  REMOVE_LIQUIDITY = 'RemoveLiquidity',
  BUY_TOKEN0 = 'BuyToken0',
  SELL_TOKEN0 = 'SellToken0'
}

export interface Transaction {
  transactionId: number
  transactionType: TransactionType
  from: Account
  amount0In?: string
  amount1In?: string
  amount0Out?: string
  amount1Out?: string
  liquidity?: string
  createdAt: number
}

export interface TransactionExt {
  // eslint-disable-next-line camelcase
  transaction_id: number
  // eslint-disable-next-line camelcase
  transaction_type: TransactionType
  // eslint-disable-next-line camelcase
  from_account: string
  // eslint-disable-next-line camelcase
  amount_0_in?: string
  // eslint-disable-next-line camelcase
  amount_1_in?: string
  // eslint-disable-next-line camelcase
  amount_0_out?: string
  // eslint-disable-next-line camelcase
  amount_1_out?: string
  liquidity?: string
  // eslint-disable-next-line camelcase
  created_at: string
  price: string
  volume: string
  direction: string
  // eslint-disable-next-line camelcase
  token_reversed: boolean
}
