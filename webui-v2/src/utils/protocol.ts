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

  pools.forEach((pool) => {
    const token0 = String(pool.token0)
    const token1 = String(pool.token1 ?? constants.LINERA_NATIVE_ID)

    if (token0 === constants.LINERA_NATIVE_ID) {
      const token1NativePrice = finiteOrUndefined(pool.token1Price)
      if (token1NativePrice) priceMap.set(token1, token1NativePrice)
      return
    }

    if (token1 === constants.LINERA_NATIVE_ID) {
      const token0NativePrice = finiteOrUndefined(pool.token0Price)
      if (token0NativePrice) priceMap.set(token0, token0NativePrice)
    }
  })

  return priceMap
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
