export enum API {
  GetTransactionsForLine = '/v1/get/transactions/for/line',
}

export interface Transaction {
  ID: number;
  PoolID: number;
  TransactionID: number;
  TransactionType: string;
  ChainID: string;
  Owner: string;
  AmountZeroIn: number;
  AmountOneIn: number;
  AmountZeroOut: number;
  AmountOneOut: number;
  Timestamp: number;
}

export interface GetTransactionsForLineResponse {
  OriginalTxID: number;
  PoolID: number;
  Transactions: Transaction[];
  Limit: number;
  Offset: number;
}
