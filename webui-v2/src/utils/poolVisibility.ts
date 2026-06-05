import { type Pool } from 'src/__generated__/graphql/swap/graphql'

const positiveAmount = (value: string | number | null | undefined) => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0
}

export const isFinalizedPool = (pool: Pick<Pool, 'reserve0' | 'reserve1'>) => {
  return positiveAmount(pool.reserve0) && positiveAmount(pool.reserve1)
}

export const visiblePools = (pools: Pool[]) => pools.filter(isFinalizedPool)
