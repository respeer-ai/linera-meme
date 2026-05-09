import { constants } from 'src/constant'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { type PoolStat } from 'src/stores/kline'

export const protocolSwapFeeRate = (): number => constants.PROTOCOL_SWAP_FEE_RATE

export const protocolSwapFeePercentLabel = (): string => constants.PROTOCOL_SWAP_FEE_PERCENT_LABEL

export const calculateSwapFeeAmount = (amount: number): number => {
  if (!Number.isFinite(amount) || amount <= 0) return 0
  return amount * protocolSwapFeeRate()
}

export const applySwapFee = (amount: number): number => {
  if (!Number.isFinite(amount) || amount <= 0) return 0
  return amount * (1 - protocolSwapFeeRate())
}

export const calculateConstantProductPriceImpact = (
  reserveIn: number,
  reserveOut: number,
  amountIn: number,
): number => {
  if (
    !Number.isFinite(reserveIn) ||
    !Number.isFinite(reserveOut) ||
    !Number.isFinite(amountIn) ||
    reserveIn <= 0 ||
    reserveOut <= 0 ||
    amountIn <= 0
  ) {
    return 0
  }

  const amountInAfterFee = applySwapFee(amountIn)
  if (amountInAfterFee <= 0) return 0

  const midPrice = reserveOut / reserveIn
  if (!Number.isFinite(midPrice) || midPrice <= 0) return 0

  const idealOutput = amountInAfterFee * midPrice
  if (!Number.isFinite(idealOutput) || idealOutput <= 0) return 0

  const invariant = reserveIn * reserveOut
  const newReserveIn = reserveIn + amountInAfterFee
  const newReserveOut = invariant / newReserveIn
  const actualOutput = reserveOut - newReserveOut

  return (idealOutput - actualOutput) / idealOutput
}

export const calculatePoolAprFromDailyVolume = (dailyVolume: number, tvl: number): number => {
  if (!Number.isFinite(dailyVolume) || !Number.isFinite(tvl) || dailyVolume <= 0 || tvl <= 0) {
    return 0
  }

  return ((dailyVolume * protocolSwapFeeRate()) / tvl) * 365
}

const finiteOrUndefined = (value: string | number | null | undefined): number | undefined => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined
}

export const buildNativePriceMap = (pools: Pool[]): Map<string, number> => {
  const priceMap = new Map<string, number>([[constants.LINERA_NATIVE_ID, 1]])
  let changed = true
  while (changed) {
    changed = false
    pools.forEach((pool) => {
      const token0 = String(pool.token0)
      const token1 = String(pool.token1 ?? constants.LINERA_NATIVE_ID)
      const token0Price = finiteOrUndefined(pool.token0Price)
      const token1Price = finiteOrUndefined(pool.token1Price)
      const known0 = priceMap.get(token0)
      const known1 = priceMap.get(token1)

      if (known0 !== undefined && token1Price !== undefined && priceMap.get(token1) === undefined) {
        priceMap.set(token1, known0 * token1Price)
        changed = true
      }

      if (known1 !== undefined && token0Price !== undefined && priceMap.get(token0) === undefined) {
        priceMap.set(token0, known1 * token0Price)
        changed = true
      }
    })
  }

  return priceMap
}

export const calculateTransactionValueInNative = (
  transaction: {
    direction?: string
    amount_0_in?: string | null
    amount_0_out?: string | null
    amount_1_in?: string | null
    amount_1_out?: string | null
  },
  pool: Pick<Pool, 'token0' | 'token1'> | undefined,
  nativePriceMap: Map<string, number>,
): number | undefined => {
  if (!pool) return undefined

  const token0 = String(pool.token0)
  const token1 = String(pool.token1 ?? constants.LINERA_NATIVE_ID)
  const token0Price = nativePriceMap.get(token0)
  const token1Price = nativePriceMap.get(token1)

  if (transaction.direction === 'Buy') {
    const amount1In = finiteOrUndefined(transaction.amount_1_in)
    if (amount1In !== undefined && token1Price !== undefined) return amount1In * token1Price
  }

  if (transaction.direction === 'Sell') {
    const amount0In = finiteOrUndefined(transaction.amount_0_in)
    if (amount0In !== undefined && token0Price !== undefined) return amount0In * token0Price
  }

  const amount0 = finiteOrUndefined(transaction.amount_0_in) ?? finiteOrUndefined(transaction.amount_0_out)
  if (amount0 !== undefined && token0Price !== undefined) return amount0 * token0Price

  const amount1 = finiteOrUndefined(transaction.amount_1_in) ?? finiteOrUndefined(transaction.amount_1_out)
  if (amount1 !== undefined && token1Price !== undefined) return amount1 * token1Price

  return undefined
}

export const calculatePoolTvlInNative = (
  pool: Pool,
  nativePriceMap: Map<string, number>,
): number | undefined => {
  const token0 = String(pool.token0)
  const token1 = String(pool.token1 ?? constants.LINERA_NATIVE_ID)
  const reserve0 = finiteOrUndefined(pool.reserve0)
  const reserve1 = finiteOrUndefined(pool.reserve1)
  const token0Price = nativePriceMap.get(token0)
  const token1Price = nativePriceMap.get(token1)

  if (!reserve0 || !reserve1 || !token0Price || !token1Price) return undefined

  return reserve0 * token0Price + reserve1 * token1Price
}

export const calculatePoolVolumeInNative = (
  poolStat: PoolStat | undefined,
  nativePriceMap: Map<string, number>,
): number | undefined => {
  if (!poolStat) return undefined

  const token1 = String(poolStat.token_1 ?? constants.LINERA_NATIVE_ID)
  const token1Price = nativePriceMap.get(token1)
  const volume = finiteOrUndefined(poolStat.volume)

  if (!volume || !token1Price) return undefined

  return volume * token1Price
}
