import { type Account } from '../account';

export enum TransactionType {
  ADD_LIQUIDITY = 'AddLiquidity',
  REMOVE_LIQUIDITY = 'RemoveLiquidity',
  BUY_TOKEN0 = 'BuyToken0',
  SELL_TOKEN0 = 'SellToken0',
}

export interface Transaction {
  transactionId: number;
  transactionType: TransactionType;
  from: Account;
  amount0In?: string;
  amount1In?: string;
  amount0Out?: string;
  amount1Out?: string;
  liquidity?: string;
  createdAt: number;
}

export interface TransactionExt {
  transaction_id: number;
  transaction_type: TransactionType;
  from_account: string;
  amount_0_in?: string;
  amount_1_in?: string;
  amount_0_out?: string;
  amount_1_out?: string;
  liquidity?: string;
  created_at: number;
  created_timestamp: number;
  price: string;
  volume: string;
  direction: string;
  token_reversed: number;
}
