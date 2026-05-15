import { describe, expect, test } from 'bun:test'

import { dbKline } from 'src/controller'
import { Interval } from 'src/stores/kline/const'

import { Kline } from './kline'

const token0 = 'token-a'
const token1 = 'token-b'
const poolId = 1
const poolApplication = 'pool-app'
const interval = Interval.FIVE_MINUTE
const timestamp = 1_000

const point = (overrides: Partial<Parameters<typeof Kline.bulkPut>[5][number]> = {}) => ({
  timestamp,
  bucket_start_ms: timestamp,
  bucket_end_ms: timestamp + 299_999,
  is_final: false,
  open: 1,
  high: 2,
  low: 0.5,
  close: 1.5,
  base_volume: 10,
  quote_volume: 15,
  ...overrides,
})

describe('Kline bulkPut persistence', () => {
  const originalKlinePoints = dbKline.klinePoints

  test('fetch persistence resolves duplicate rows through the composite index and overwrites them', async () => {
    const existing = {
      id: 9,
      token0,
      token1,
      poolId,
      poolApplication,
      interval,
      ...point(),
    }
    const updated = point({
      is_final: true,
      open: 3,
      high: 4,
      low: 2,
      close: 3.5,
      base_volume: 20,
      quote_volume: 30,
    })

    const whereCalls: unknown[] = []
    const equalsCalls: unknown[] = []
    const putCalls: unknown[] = []

    const put = (value: unknown) => {
      putCalls.push(value)
      return Promise.resolve()
    }
    const first = () => Promise.resolve(existing)
    const equals = (value: unknown) => {
      equalsCalls.push(value)
      return { first }
    }
    const where = (value: unknown) => {
      whereCalls.push(value)
      return { equals }
    }

    Object.defineProperty(dbKline, 'klinePoints', {
      configurable: true,
      value: {
        bulkPut: () => {
          const err = new Error('duplicate key') as Error & {
            name: string
            failuresByPos: Record<number, Error>
          }
          err.name = 'BulkError'
          err.failuresByPos = {
            0: new Error('duplicate key'),
          }
          return Promise.reject(err)
        },
        where,
        put,
      },
    })

    try {
      await Kline.bulkPut(token0, token1, poolId, poolApplication, interval, [updated], 'fetch')
    } finally {
      Object.defineProperty(dbKline, 'klinePoints', {
        configurable: true,
        value: originalKlinePoints,
      })
    }

    expect(whereCalls).toEqual(['[token0+token1+poolId+poolApplication+interval+timestamp]'])
    expect(equalsCalls).toEqual([[token0, token1, poolId, poolApplication, interval, timestamp]])
    expect(putCalls).toHaveLength(1)
    expect(putCalls[0]).toEqual({
      id: 9,
      token0,
      token1,
      poolId,
      poolApplication,
      interval,
      timestamp,
      bucket_start_ms: timestamp,
      bucket_end_ms: timestamp + 299_999,
      is_final: true,
      open: 3,
      high: 4,
      low: 2,
      close: 3.5,
      base_volume: 20,
      quote_volume: 30,
    })
  })
})
