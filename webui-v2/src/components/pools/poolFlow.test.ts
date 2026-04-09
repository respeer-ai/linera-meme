import { describe, expect, test } from 'bun:test'
import { constants } from 'src/constant'
import {
  buildAddLiquidityRoute,
  canAddLiquidityForPair,
  canCreatePoolForPair,
  mapPairAmountsToPoolOrder,
  normalizePoolPair,
  pairExists,
  resolveLiquiditySubmissionMode,
  resolveRoutePoolPair,
} from './poolFlow'

describe('poolFlow', () => {
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
