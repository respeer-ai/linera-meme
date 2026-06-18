import { describe, expect, test } from 'bun:test'
import { constants } from 'src/constant'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import {
  buildAddLiquidityRoute,
  buildClaimRoute,
  buildRemoveLiquidityRoute,
  canAddLiquidityForPair,
  canCreatePoolForPair,
  isFinalizedPool,
  linkedAddLiquidityAmount,
  mapPairAmountsToPoolOrder,
  normalizePoolPair,
  pairExists,
  resolveLiquiditySubmissionMode,
  resolveRouteLiquidityContext,
  resolveRoutePoolPair,
  visiblePools,
} from './poolFlow'

describe('poolFlow', () => {
  const pool = (reserve0: string | null, reserve1: string | null): Pool =>
    ({
      token0: 'meme-1',
      token1: constants.LINERA_NATIVE_ID,
      reserve0,
      reserve1,
    }) as Pool

  test('finalized pools require positive reserve facts on both sides', () => {
    expect(isFinalizedPool(pool('1', '2'))).toBe(true)
    expect(isFinalizedPool(pool(null, '2'))).toBe(false)
    expect(isFinalizedPool(pool('1', null))).toBe(false)
    expect(isFinalizedPool(pool('0', '2'))).toBe(false)
    expect(isFinalizedPool(pool('1', '0'))).toBe(false)
  })

  test('visiblePools hides unfinalized protocol catalog entries', () => {
    expect(visiblePools([pool(null, null), pool('0', '1'), pool('1', '1')])).toHaveLength(1)
  })

  test('normalizePoolPair keeps native token in token1 when one side is native', () => {
    expect(
      normalizePoolPair({
        token0: constants.LINERA_NATIVE_ID,
        token1: 'meme-1',
      }),
    ).toEqual({
      token0: 'meme-1',
      token1: constants.LINERA_NATIVE_ID,
    })
  })

  test('create pool is allowed only for non-existing pairs', () => {
    const pools = [
      {
        token0: 'meme-1',
        token1: constants.LINERA_NATIVE_ID,
      },
    ]

    expect(
      canCreatePoolForPair(pools, {
        token0: 'meme-2',
        token1: constants.LINERA_NATIVE_ID,
      }),
    ).toBe(true)

    expect(
      canCreatePoolForPair(pools, {
        token0: constants.LINERA_NATIVE_ID,
        token1: 'meme-1',
      }),
    ).toBe(false)
  })

  test('add liquidity is allowed only for existing pairs', () => {
    const pools = [
      {
        token0: 'meme-1',
        token1: 'meme-2',
      },
    ]

    expect(
      canAddLiquidityForPair(pools, {
        token0: 'meme-2',
        token1: 'meme-1',
      }),
    ).toBe(true)

    expect(
      canAddLiquidityForPair(pools, {
        token0: 'meme-3',
        token1: 'meme-1',
      }),
    ).toBe(false)
  })

  test('build add liquidity route keeps canonical pair order', () => {
    expect(
      buildAddLiquidityRoute({
        token0: constants.LINERA_NATIVE_ID,
        token1: 'meme-1',
      }),
    ).toEqual({
      path: '/pools/add-liquidity',
      query: {
        token0: 'meme-1',
        token1: constants.LINERA_NATIVE_ID,
      },
    })
  })

  test('resolveLiquiditySubmissionMode creates missing pools and adds to existing pools', () => {
    const pools = [
      {
        token0: 'meme-1',
        token1: constants.LINERA_NATIVE_ID,
      },
    ]

    expect(
      resolveLiquiditySubmissionMode(pools, {
        token0: constants.LINERA_NATIVE_ID,
        token1: 'meme-1',
      }),
    ).toBe('add-liquidity')

    expect(
      resolveLiquiditySubmissionMode(pools, {
        token0: 'meme-2',
        token1: constants.LINERA_NATIVE_ID,
      }),
    ).toBe('create-pool')
  })

  test('resolveLiquiditySubmissionMode uses the caller supplied visible pool set', () => {
    const catalogPools = [pool(null, null)]

    expect(
      resolveLiquiditySubmissionMode(visiblePools(catalogPools), {
        token0: constants.LINERA_NATIVE_ID,
        token1: 'meme-1',
      }),
    ).toBe('create-pool')
  })

  test('resolveRoutePoolPair reads and normalizes route query pairs', () => {
    expect(
      resolveRoutePoolPair({
        token0: [constants.LINERA_NATIVE_ID],
        token1: 'meme-1',
      }),
    ).toEqual({
      token0: 'meme-1',
      token1: constants.LINERA_NATIVE_ID,
    })
  })

  test('build remove liquidity route carries actual removable position amounts', () => {
    expect(
      buildRemoveLiquidityRoute(
        {
          token0: constants.LINERA_NATIVE_ID,
          token1: 'meme-1',
        },
        {
          mode: 'liquidity',
          liquidity: '1.2',
          amount0: '40.1',
          amount1: '0.03',
        },
      ),
    ).toEqual({
      path: '/pools/remove-liquidity',
      query: {
        token0: 'meme-1',
        token1: constants.LINERA_NATIVE_ID,
        mode: 'liquidity',
        liquidity: '1.2',
        amount0: '40.1',
        amount1: '0.03',
      },
    })
  })

  test('build claim route carries canonical pair and selected token', () => {
    expect(
      buildClaimRoute(
        {
          token0: constants.LINERA_NATIVE_ID,
          token1: 'meme-1',
        },
        {
          token: constants.LINERA_NATIVE_ID,
        },
      ),
    ).toEqual({
      path: '/pools/claim',
      query: {
        token0: 'meme-1',
        token1: constants.LINERA_NATIVE_ID,
        token: constants.LINERA_NATIVE_ID,
      },
    })
  })

  test('resolveRouteLiquidityContext accepts complete non-negative amount context', () => {
    expect(
      resolveRouteLiquidityContext({
        liquidity: ['1.2'],
        amount0: '40.1',
        amount1: '0.03',
      }),
    ).toEqual({
      liquidity: '1.2',
      amount0: '40.1',
      amount1: '0.03',
    })
  })

  test('resolveRouteLiquidityContext rejects missing or invalid amount context', () => {
    expect(resolveRouteLiquidityContext({ liquidity: '1', amount0: '2', amount1: undefined })).toBe(undefined)
    expect(resolveRouteLiquidityContext({ liquidity: '-1', amount0: '2', amount1: '3' })).toBe(undefined)
    expect(resolveRouteLiquidityContext({ liquidity: 'abc', amount0: '2', amount1: '3' })).toBe(undefined)
  })


  test('linkedAddLiquidityAmount derives the opposite side from pool reserves with buffer', () => {
    expect(
      linkedAddLiquidityAmount({
        pool: pool('1000', '10'),
        sourceToken: 'meme-1',
        targetToken: constants.LINERA_NATIVE_ID,
        sourceAmount: '100',
      }),
    ).toBe('1.1')

    expect(
      linkedAddLiquidityAmount({
        pool: pool('1000', '10'),
        sourceToken: constants.LINERA_NATIVE_ID,
        targetToken: 'meme-1',
        sourceAmount: '1',
      }),
    ).toBe('110')
  })


  test('linkedAddLiquidityAmount caps the calculated side by available balance', () => {
    expect(
      linkedAddLiquidityAmount({
        pool: pool('1000', '10'),
        sourceToken: 'meme-1',
        targetToken: constants.LINERA_NATIVE_ID,
        sourceAmount: '100',
        maxTargetAmount: '1',
      }),
    ).toBe('1')
  })

  test('linkedAddLiquidityAmount ignores create-pool or incomplete reserve inputs', () => {
    expect(
      linkedAddLiquidityAmount({
        pool: pool(null, '10'),
        sourceToken: 'meme-1',
        targetToken: constants.LINERA_NATIVE_ID,
        sourceAmount: '100',
      }),
    ).toBe('')

    expect(
      linkedAddLiquidityAmount({
        pool: pool('1000', '10'),
        sourceToken: 'meme-1',
        targetToken: constants.LINERA_NATIVE_ID,
        sourceAmount: '',
      }),
    ).toBe('')
  })

  test('mapPairAmountsToPoolOrder aligns user input to canonical pool order', () => {
    expect(
      mapPairAmountsToPoolOrder({
        selectedToken0: constants.LINERA_NATIVE_ID,
        selectedToken1: 'meme-1',
        amountForSelectedToken0: '1.5',
        amountForSelectedToken1: '200',
        canonicalPair: {
          token0: 'meme-1',
          token1: constants.LINERA_NATIVE_ID,
        },
      }),
    ).toEqual({
      amount0: '200',
      amount1: '1.5',
    })
  })

  test('pairExists treats reversed ordering as the same pool pair', () => {
    expect(
      pairExists(
        [
          {
            token0: 'meme-1',
            token1: 'meme-2',
          },
        ],
        {
          token0: 'meme-2',
          token1: 'meme-1',
        },
      ),
    ).toBe(true)
  })
})
