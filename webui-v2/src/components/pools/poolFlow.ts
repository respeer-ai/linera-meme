import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { constants } from 'src/constant'

export interface PoolPairLike {
  token0: string
  token1?: string
}

export interface CanonicalPoolPair {
  token0: string
  token1: string
}

export interface PoolFlowRoute {
  path: string
  query?: {
    token0: string
    token1: string
  }
}

export type LiquiditySubmissionMode = 'create-pool' | 'add-liquidity'

const readQueryValue = (value: unknown) => {
  if (typeof value === 'string') return value
  if (Array.isArray(value) && typeof value[0] === 'string') return value[0]
  return undefined
}

export const normalizePoolPair = (pair: PoolPairLike): CanonicalPoolPair => {
  const token1 = pair.token1 || constants.LINERA_NATIVE_ID

  if (pair.token0 === constants.LINERA_NATIVE_ID && token1 !== constants.LINERA_NATIVE_ID) {
    return {
      token0: token1,
      token1: pair.token0,
    }
  }

  if (
    pair.token0 !== constants.LINERA_NATIVE_ID &&
    token1 !== constants.LINERA_NATIVE_ID &&
    pair.token0 > token1
  ) {
    return {
      token0: token1,
      token1: pair.token0,
    }
  }

  return {
    token0: pair.token0,
    token1,
  }
}

export const pairExists = (pools: PoolPairLike[], pair: PoolPairLike) => {
  const normalizedPair = normalizePoolPair(pair)

  return pools.some((pool) => {
    const normalizedPool = normalizePoolPair(pool)
    return (
      normalizedPool.token0 === normalizedPair.token0 &&
      normalizedPool.token1 === normalizedPair.token1
    )
  })
}

export const findPoolByPair = (pools: Pool[], pair: PoolPairLike) => {
  const normalizedPair = normalizePoolPair(pair)
  return pools.find((pool) => {
    const normalizedPool = normalizePoolPair(pool)
    return (
      normalizedPool.token0 === normalizedPair.token0 &&
      normalizedPool.token1 === normalizedPair.token1
    )
  })
}

export const canCreatePoolForPair = (pools: PoolPairLike[], pair: PoolPairLike) => {
  const normalizedPair = normalizePoolPair(pair)
  if (normalizedPair.token0 === normalizedPair.token1) return false
  if (normalizedPair.token0 === constants.LINERA_NATIVE_ID) return false
  return !pairExists(pools, normalizedPair)
}

export const canAddLiquidityForPair = (pools: PoolPairLike[], pair: PoolPairLike) => {
  const normalizedPair = normalizePoolPair(pair)
  if (normalizedPair.token0 === normalizedPair.token1) return false
  return pairExists(pools, normalizedPair)
}

export const buildAddLiquidityRoute = (pair?: PoolPairLike): PoolFlowRoute => {
  if (!pair) {
    return {
      path: '/pools/add-liquidity',
    }
  }

  return {
    path: '/pools/add-liquidity',
    query: normalizePoolPair(pair),
  }
}

export const buildRemoveLiquidityRoute = (pair?: PoolPairLike): PoolFlowRoute => {
  if (!pair) {
    return {
      path: '/pools/remove-liquidity',
    }
  }

  return {
    path: '/pools/remove-liquidity',
    query: normalizePoolPair(pair),
  }
}

export const resolveRoutePoolPair = ({
  token0,
  token1,
}: {
  token0: unknown
  token1: unknown
}) => {
  const requestedToken0 = readQueryValue(token0)
  const requestedToken1 = readQueryValue(token1)

  if (!requestedToken0 || !requestedToken1 || requestedToken0 === requestedToken1) {
    return undefined
  }

  return normalizePoolPair({
    token0: requestedToken0,
    token1: requestedToken1,
  })
}

export const resolveLiquiditySubmissionMode = (
  pools: PoolPairLike[],
  pair: PoolPairLike,
): LiquiditySubmissionMode => {
  return pairExists(pools, pair) ? 'add-liquidity' : 'create-pool'
}

export const mapPairAmountsToPoolOrder = ({
  selectedToken0,
  selectedToken1,
  amountForSelectedToken0,
  amountForSelectedToken1,
  canonicalPair,
}: {
  selectedToken0: string
  selectedToken1: string
  amountForSelectedToken0: string
  amountForSelectedToken1: string
  canonicalPair: PoolPairLike
}) => {
  const normalizedPair = normalizePoolPair(canonicalPair)

  if (
    selectedToken0 === normalizedPair.token0 &&
    selectedToken1 === normalizedPair.token1
  ) {
    return {
      amount0: amountForSelectedToken0,
      amount1: amountForSelectedToken1,
    }
  }

  return {
    amount0: amountForSelectedToken1,
    amount1: amountForSelectedToken0,
  }
}
