export enum API {
  GetLastTranscation = '/v1/get/token/last/cond',
  GetLastTransactions = '/v1/get/token/last/conds',
  ExistToken = '/v1/exit/token/by/symbol'
}

export interface LastTranscation {
  PoolID: number;
  TokenZeroAddress: string;
  TokenOneAddress: string;
  LastTxAt: number;
  LastTxZeroAmount: string;
  LastTxOneAmount: string;
  OneDayZeroAmountVolumn: string;
  OneDayOneAmountVolumn: string;
  NowPrice: string;
  OneDayIncresePercent: string;
}

export interface GetLastTranscationRequest {
  PoolID: number;
  TokenZeroAddress: string;
  TokenOneAddress: string;
}

export interface GetLastTranscationResponse {
  Info: LastTranscation;
}

export interface PoolTokenCond {
  PoolID: number;
  TokenZeroAddress: string;
  TokenOneAddress: string;
}
export interface GetLastTransactionsRequest {
  PoolTokenConds: Array<PoolTokenCond>
}

export interface GetLastTransactionsResponse {
  Infos: Array<LastTranscation>;
}

export interface ExistTokenRequest {
  Symbol: string;
}

export interface ExistTokenResponse {
  Exist: boolean;
}
