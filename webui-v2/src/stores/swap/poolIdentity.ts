import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { _Account, type Account } from '../account'

export const poolApplicationKey = (pool: Pick<Pool, 'poolApplication'>): string => {
  return _Account.poolApplicationDescription(pool.poolApplication as Account) || ''
}

export const poolIdentityKey = (pool: Pick<Pool, 'poolId' | 'poolApplication'>): string => {
  return `${pool.poolId}:${poolApplicationKey(pool)}`
}

export const findPoolByIdentity = (
  pools: Pool[],
  poolId: number | string,
  poolApplication?: string,
): Pool | undefined => {
  if (poolApplication) {
    const pool = pools.find((el) => poolApplicationKey(el) === poolApplication)
    if (pool) return pool
  }

  return pools.find((el) => Number(el.poolId) === Number(poolId))
}
