import { describe, expect, test } from 'bun:test'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { findPoolByIdentity, poolApplicationKey, poolIdentityKey } from './poolIdentity'

const pool = (poolId: number, owner: string, chainId: string, token0 = 'MEME'): Pool =>
  ({
    __typename: 'Pool',
    poolId,
    token0,
    token1: null,
    poolApplication: {
      chain_id: chainId,
      owner,
    },
  }) as Pool

describe('pool identity', () => {
  test('formats pool application like Linera account descriptions', () => {
    const target = pool(1000, 'e90a', 'chain-a')

    expect(poolApplicationKey(target)).toBe('0xe90a@chain-a')
    expect(poolIdentityKey(target)).toBe('1000:0xe90a@chain-a')
  })

  test('prefers pool application over pool id when matching projection rows', () => {
    const wrongPool = pool(1, 'aaaa', 'chain-a', 'WRONG')
    const expectedPool = pool(1000, 'bbbb', 'chain-b', 'MEME')

    expect(findPoolByIdentity([wrongPool, expectedPool], 1, '0xbbbb@chain-b')).toBe(expectedPool)
  })

  test('falls back to pool id for legacy callers without pool application', () => {
    const expectedPool = pool(1000, 'bbbb', 'chain-b', 'MEME')

    expect(findPoolByIdentity([expectedPool], '1000')).toBe(expectedPool)
  })
})
