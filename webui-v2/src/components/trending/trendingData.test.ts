import { describe, expect, test } from 'bun:test'

import { buildTrendingBulletins } from './trendingData'
import { constants } from 'src/constant'
import { type Application } from 'src/stores/ams'
import { type TickerStat } from 'src/stores/kline'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { StoreType } from 'src/stores/store'

const application = (
  applicationId: string,
  ticker: string,
  name: string,
  createdAt: number,
): Application => ({
  creator: 'creator',
  applicationName: name,
  applicationId,
  applicationType: 'meme',
  keyWords: [],
  logoStoreType: StoreType.Blob,
  logo: `${ticker}.png`,
  description: '',
  website: '',
  spec: JSON.stringify({
    ticker,
    name,
    totalSupply: '1000000',
  }),
  createdAt,
})

const tickerStat = (
  token: string,
  priceNow: string,
  priceStart: string,
  volume: string,
): TickerStat => ({
  token,
  high: priceNow,
  low: priceStart,
  volume,
  tx_count: 10,
  price_now: priceNow,
  price_start: priceStart,
})

const pool = (token0: string, token0Price: string): Pool =>
  ({
    __typename: 'Pool',
    creator: 'creator',
    poolId: Number(token0.slice(-1)),
    token0,
    token1: constants.LINERA_NATIVE_ID,
    poolApplication: `pool-${token0}`,
    latestTransaction: null,
    token0Price,
    token1Price: '1',
    reserve0: '100',
    reserve1: '100',
    createdAt: 0,
  }) as Pool

describe('buildTrendingBulletins', () => {
  const applications: Application[] = [
    application('token-a', 'AAA', 'Alpha', 1_710_000_000_000),
    application('token-b', 'BBB', 'Beta', 1_710_000_600_000),
    application('token-c', 'CCC', 'Gamma', 1_710_001_200_000),
  ]
  const firstApplication = applications[0] as Application

  const tickersByToken = new Map<string, TickerStat>([
    ['token-a', tickerStat('token-a', '1.50', '1.00', '200.25')],
    ['token-b', tickerStat('token-b', '0.80', '1.00', '900.00')],
    ['token-c', tickerStat('token-c', '1.10', '1.00', '500.50')],
  ])

  const poolsByToken = new Map<string, Pool>([
    ['token-a', pool('token-a', '0.123456')],
    ['token-b', pool('token-b', '0.654321')],
    ['token-c', pool('token-c', '0.222222')],
  ])

  test('ranks top gainers by real percentage change instead of placeholders', () => {
    const items = buildTrendingBulletins('gainers', {
      applications,
      tickersByToken,
      poolsByToken,
      applicationLogo: (item) => `/logo/${item.applicationId}.png`,
      limit: 2,
      nowMs: 1_710_010_000_000,
    })

    expect(items).toHaveLength(2)
    expect(items[0]?.label).toBe('AAA')
    expect(items[0]?.subtitle).toBe('Alpha')
    expect(items[0]?.value).toBe('0.123456')
    expect(items[0]?.caption).toBe('+50.00%')
    expect(items[0]?.imageBorderColor).toBe('primary-twenty-five')
    expect(items[0]?.captionColor).toBe('secondary')
    expect(items[1]?.label).toBe('CCC')
    expect(items[1]?.caption).toBe('+10.00%')
  })

  test('ranks top volume by ticker volume and renders native quote volume text', () => {
    const items = buildTrendingBulletins('volume', {
      applications,
      tickersByToken,
      poolsByToken,
      applicationLogo: () => '/logo.png',
      limit: 2,
      nowMs: 1_710_010_000_000,
    })

    expect(items.map((item) => item.label)).toEqual(['BBB', 'CCC'])
    expect(items[0]?.caption).toBe('900.0000 TLINERA')
    expect(items[0]?.imageBorderColor).toBe('secondary-twenty-five')
    expect(items[0]?.captionColor).toBe('volume')
  })

  test('ranks new tokens by creation time and formats token age caption', () => {
    const items = buildTrendingBulletins('new', {
      applications,
      tickersByToken,
      poolsByToken,
      applicationLogo: () => '/logo.png',
      limit: 3,
      nowMs: 1_710_001_500_000,
    })

    expect(items.map((item) => item.label)).toEqual(['CCC', 'BBB', 'AAA'])
    expect(items[0]?.caption).toBe('5m ago')
    expect(items[0]?.imageBorderColor).toBe('neutral-twenty-five')
    expect(items[0]?.captionColor).toBe('warning')
  })

  test('keeps tokens without stats renderable with deterministic zeroed captions', () => {
    const items = buildTrendingBulletins('gainers', {
      applications: [firstApplication],
      tickersByToken: new Map(),
      poolsByToken: new Map(),
      applicationLogo: () => '/logo.png',
      limit: 1,
      nowMs: 1_710_010_000_000,
    })

    expect(items[0]?.label).toBe('AAA')
    expect(items[0]?.value).toBe('0.000000')
    expect(items[0]?.caption).toBe('+0.00%')
  })
})
