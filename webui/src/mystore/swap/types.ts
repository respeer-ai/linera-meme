export enum API {
  GetTokens = '/v1/get/tokens',
  GetTokenPairs = '/v1/get/token/pairs',
  GetBalance = '/v1/get/tokens',
  GetKPointTypes = '/v1/get/kpoint/types',
}

export interface Token {
  ID: number;
  Address: string;
  Site: string;
  IconStoreType: string
  Icon: string;
  Name: string;
  Symbol: string;
  CreatedAt: number;
  UpdatedAt: number;
}

export interface GetTokensResponse {
  Infos: Token[];
}

export interface TokenPair {
  ID: number;
  PoolID: number;
  TokenZeroID: number;
  TokenZeroName: string;
  TokenZeroAddress: string;
  TokenZeroIconStoreType: string
  TokenZeroIcon: string;
  TokenZeroSymbol: string;
  TokenOneID: number;
  TokenOneName: string;
  TokenOneAddress: string;
  TokenOneIconStoreType: string
  TokenOneIcon: string;
  TokenOneSymbol: string;
  Remark: string;
  CreatedAt: number;
  UpdatedAt: number;
}

export interface GetTokenPairsResponse {
  Infos: TokenPair[];
}

export interface Balance {
  balanceOf: string;
}

export interface BalanceResponse {
  data: Balance;
}

export interface CalSwapAmount {
  calculateSwapAmount: number;
}

export interface CalSwapAmountResponse {
  data: CalSwapAmount;
}

export interface KPointTypeInfo {
  KPointType: string
  ShortName: string
  Seconds: number
}

export interface GetKPointTypesResponse {
  Infos: KPointTypeInfo[]
}
