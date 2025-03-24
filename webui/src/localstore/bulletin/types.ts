export enum API {
  GetOneDayVolumn = '/v1/get/one/day/volumn',
}

export interface TokenVolumn {
  PoolID: number
  Address: string
  Name: string
  Icon: string
  Symbol: string
  Amount: number
}

export interface GetOneDayVolumnResponse {
  Infos: TokenVolumn[];
}
