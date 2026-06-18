import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { constants } from 'src/constant'

export { isFinalizedPool, visiblePools } from 'src/utils/poolVisibility'

export interface PoolPairLike {
  token0: string
  token1?: string
}

export interface CanonicalPoolPair {
  token0: string
  token1: string
}

export type RemoveLiquidityMode = 'liquidity' | 'fees'

export interface RemoveLiquidityContext {
  mode?: RemoveLiquidityMode
  liquidity?: string
  amount0?: string
  amount1?: string
}

export interface ClaimContext {
  token?: string
  poolApplication?: string
}

export interface PoolFlowRoute {
  path: string
  query?: {
    token0: string
    token1: string
    mode?: RemoveLiquidityMode
    liquidity?: string
    amount0?: string
    amount1?: string
    token?: string
    poolApplication?: string
  }
}

export type RouteLiquidityContext = Required<Pick<RemoveLiquidityContext, 'liquidity' | 'amount0' | 'amount1'>>

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

export const buildRemoveLiquidityRoute = (pair?: PoolPairLike, context: RemoveLiquidityContext = {}): PoolFlowRoute => {
  if (!pair) {
    return {
      path: '/pools/remove-liquidity',
    }
  }

  return {
    path: '/pools/remove-liquidity',
    query: {
      ...normalizePoolPair(pair),
      ...context,
    },
  }
}

export const buildClaimRoute = (pair?: PoolPairLike, context: ClaimContext = {}): PoolFlowRoute => {
  if (!pair) {
    return {
      path: '/pools/claim',
    }
  }

  return {
    path: '/pools/claim',
    query: {
      ...normalizePoolPair(pair),
      ...context,
    },
  }
}

export const resolveRoutePoolPair = ({ token0, token1 }: { token0: unknown; token1: unknown }) => {
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

const validRouteAmount = (value: string | undefined) => {
  if (value === undefined || value.trim() === '') return undefined
  const numeric = Number.parseFloat(value)
  if (!Number.isFinite(numeric) || numeric < 0) return undefined
  return value
}

export const resolveRouteLiquidityContext = ({
  liquidity,
  amount0,
  amount1,
}: {
  liquidity: unknown
  amount0: unknown
  amount1: unknown
}): RouteLiquidityContext | undefined => {
  const routeLiquidity = validRouteAmount(readQueryValue(liquidity))
  const routeAmount0 = validRouteAmount(readQueryValue(amount0))
  const routeAmount1 = validRouteAmount(readQueryValue(amount1))

  if (routeLiquidity === undefined || routeAmount0 === undefined || routeAmount1 === undefined) {
    return undefined
  }

  return {
    liquidity: routeLiquidity,
    amount0: routeAmount0,
    amount1: routeAmount1,
  }
}

export const resolveLiquiditySubmissionMode = (
  pools: PoolPairLike[],
  pair: PoolPairLike,
): LiquiditySubmissionMode => {
  return pairExists(pools, pair) ? 'add-liquidity' : 'create-pool'
}


const validPositiveNumber = (value: string | null | undefined) => {
  const number = Number(value)
  return Number.isFinite(number) && number > 0 ? number : undefined
}

export const formatLiquidityInputAmount = (value: number) => {
  if (!Number.isFinite(value) || value <= 0) return ''
  return value.toFixed(8).replace(/\.?0+$/, '')
}

export const linkedAddLiquidityAmount = ({
  pool,
  sourceToken,
  targetToken,
  sourceAmount,
  bufferMultiplier = 1.1,
  maxTargetAmount,
}: {
  pool: Pool
  sourceToken: string
  targetToken: string
  sourceAmount: string
  bufferMultiplier?: number
  maxTargetAmount?: string
}) => {
  const poolToken0 = pool.token0
  const poolToken1 = pool.token1 || constants.LINERA_NATIVE_ID
  const reserve0 = validPositiveNumber(pool.reserve0)
  const reserve1 = validPositiveNumber(pool.reserve1)
  const amount = validPositiveNumber(sourceAmount)
  if (!reserve0 || !reserve1 || !amount) return ''

  const reserveByToken = new Map<string, number>([
    [poolToken0, reserve0],
    [poolToken1, reserve1],
  ])
  const sourceReserve = reserveByToken.get(sourceToken)
  const targetReserve = reserveByToken.get(targetToken)
  if (!sourceReserve || !targetReserve) return ''

  const calculated = amount * targetReserve / sourceReserve * bufferMultiplier
  const targetMax = validPositiveNumber(maxTargetAmount)
  return formatLiquidityInputAmount(targetMax ? Math.min(calculated, targetMax) : calculated)
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

  if (selectedToken0 === normalizedPair.token0 && selectedToken1 === normalizedPair.token1) {
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
