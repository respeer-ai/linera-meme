export interface Balance {
  balanceOf: string;
}

export interface GetBalanceResponse {
  data: Balance;
}

export interface Liquidity {
  getOwnerLiquidity: string
}

export interface GetLiquidityResponse {
  data: Liquidity;
}

export interface CalSwapAmount {
  calculateSwapAmount: number;
}

export interface CalSwapAmountResponse {
  data: CalSwapAmount;
}

export interface SwapAmountResponse {
  data: CalSwapAmount;
}
