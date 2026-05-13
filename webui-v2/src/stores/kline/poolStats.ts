import type { PoolStat } from './types'

export const normalizePoolStatId = (poolId: number | string): number | undefined => {
  if (typeof poolId === 'string' && poolId.trim() === '') return undefined

  const normalized = Number(poolId)
  return Number.isInteger(normalized) && normalized >= 0 ? normalized : undefined
}

export const buildPoolStatsMap = (stats: PoolStat[]): Map<number, PoolStat> => {
  const entries = stats
    .map((stat): [number, PoolStat] | undefined => {
      const poolId = normalizePoolStatId(stat.pool_id)
      return poolId === undefined ? undefined : [poolId, stat]
    })
    .filter((entry): entry is [number, PoolStat] => entry !== undefined)

  return new Map<number, PoolStat>(entries)
}

export const buildPoolStatsByApplicationMap = (stats: PoolStat[]): Map<string, PoolStat> => {
  return new Map<string, PoolStat>(
    stats
      .filter((stat) => typeof stat.pool_application === 'string' && stat.pool_application !== '')
      .map((stat) => [stat.pool_application as string, stat]),
  )
}

export const findPoolStat = (
  stats: Map<number, PoolStat> | undefined,
  poolId: number | string,
): PoolStat | undefined => {
  const normalizedPoolId = normalizePoolStatId(poolId)
  return normalizedPoolId === undefined ? undefined : stats?.get(normalizedPoolId)
}

export const findPoolStatByIdentity = (
  statsByPoolId: Map<number, PoolStat> | undefined,
  statsByApplication: Map<string, PoolStat> | undefined,
  poolId: number | string,
  poolApplication?: string,
): PoolStat | undefined => {
  if (poolApplication) {
    const stat = statsByApplication?.get(poolApplication)
    if (stat) return stat
  }

  return findPoolStat(statsByPoolId, poolId)
}
