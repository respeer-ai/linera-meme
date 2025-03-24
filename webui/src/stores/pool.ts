export interface Pool {
  id: number
  kLast: string
  poolFeePercent: string
  price0Cumulative: string
  price1Cumulative: string
  protocolFeePercent: string
  reserve0: string
  reserve1: string
  token0: string
  token1: string
  amount0Initial: string
  amount1Initial: string
  blockTimestamp: number
  feeTo: string
  feeToSetter: string
  erc20: string
}
