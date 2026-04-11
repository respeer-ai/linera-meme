import { constants } from 'src/constant'
import { type BulletinItem } from '../bulletin/BulletinItem'
import { type Application } from 'src/stores/ams'
import { type Meme } from 'src/stores/meme'
import { type TickerStat } from 'src/stores/kline'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'

export interface TrendingDependencies {
  applications: Application[]
  tickersByToken: Map<string, TickerStat>
  poolsByToken: Map<string, Pool>
  applicationLogo: (application: Application) => string
  nowMs?: number
  limit?: number
}

type TrendingKind = 'gainers' | 'volume' | 'new'

interface TrendingTokenEntry {
  application: Application
  meme: Meme
  pool: Pool | undefined
  price: number
  changePercent: number
  volume: number
}

const DEFAULT_LIMIT = 5

const parseMeme = (application: Application): Meme => JSON.parse(application.spec) as Meme

const parseNumber = (value: string | number | null | undefined): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const calculatePrice = (application: Application, pool?: Pool): number => {
  if (!pool) return 0

  const rawPrice = application.applicationId === pool.token0 ? pool.token0Price : pool.token1Price

  return parseNumber(rawPrice)
}

const calculateChangePercent = (ticker?: TickerStat): number => {
  if (!ticker) return 0

  const priceStart = parseNumber(ticker.price_start)
  const priceNow = parseNumber(ticker.price_now)
  if (priceStart <= 0) return 0

  return ((priceNow - priceStart) / priceStart) * 100
}

const buildEntries = ({
  applications,
  tickersByToken,
  poolsByToken,
}: TrendingDependencies): TrendingTokenEntry[] => {
  return applications.map((application) => {
    const meme = parseMeme(application)
    const ticker = tickersByToken.get(application.applicationId)
    const pool = poolsByToken.get(application.applicationId)

    return {
      application,
      meme,
      pool,
      price: calculatePrice(application, pool),
      changePercent: calculateChangePercent(ticker),
      volume: parseNumber(ticker?.volume),
    }
  })
}

const formatPrice = (price: number): string => price.toFixed(6)

const formatPercent = (value: number): string => `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`

const formatVolume = (value: number): string => `${value.toFixed(4)} ${constants.LINERA_TICKER}`

const formatAge = (createdAt: number, nowMs: number): string => {
  const deltaMs = Math.max(0, nowMs - createdAt)
  const minuteMs = 60 * 1000
  const hourMs = 60 * minuteMs
  const dayMs = 24 * hourMs

  if (deltaMs < hourMs) {
    return `${Math.max(1, Math.floor(deltaMs / minuteMs))}m ago`
  }
  if (deltaMs < dayMs) {
    return `${Math.floor(deltaMs / hourMs)}h ago`
  }

  return `${Math.floor(deltaMs / dayMs)}d ago`
}

const sortEntries = (entries: TrendingTokenEntry[], kind: TrendingKind): TrendingTokenEntry[] => {
  if (kind === 'gainers') {
    return [...entries].sort((left, right) => {
      if (right.changePercent !== left.changePercent)
        return right.changePercent - left.changePercent
      if (right.volume !== left.volume) return right.volume - left.volume
      return right.application.createdAt - left.application.createdAt
    })
  }

  if (kind === 'volume') {
    return [...entries].sort((left, right) => {
      if (right.volume !== left.volume) return right.volume - left.volume
      if (right.changePercent !== left.changePercent)
        return right.changePercent - left.changePercent
      return right.application.createdAt - left.application.createdAt
    })
  }

  return [...entries].sort(
    (left, right) => right.application.createdAt - left.application.createdAt,
  )
}

const toBulletinItem = (
  entry: TrendingTokenEntry,
  applicationLogo: (application: Application) => string,
  kind: TrendingKind,
  nowMs: number,
): BulletinItem => {
  const common = {
    image: applicationLogo(entry.application),
    label: entry.meme.ticker,
    subtitle: entry.meme.name,
    value: formatPrice(entry.price),
    valueColor: 'light',
  }

  if (kind === 'gainers') {
    return {
      ...common,
      imageBorderColor: 'primary-twenty-five',
      caption: formatPercent(entry.changePercent),
      captionColor: entry.changePercent >= 0 ? 'secondary' : 'negative',
    }
  }

  if (kind === 'volume') {
    return {
      ...common,
      imageBorderColor: 'secondary-twenty-five',
      caption: formatVolume(entry.volume),
      captionColor: 'volume',
    }
  }

  return {
    ...common,
    imageBorderColor: 'neutral-twenty-five',
    caption: formatAge(entry.application.createdAt, nowMs),
    captionColor: 'warning',
  }
}

export const buildTrendingBulletins = (
  kind: TrendingKind,
  dependencies: TrendingDependencies,
): BulletinItem[] => {
  const nowMs = dependencies.nowMs ?? Date.now()
  const limit = dependencies.limit ?? DEFAULT_LIMIT
  const entries = buildEntries(dependencies)

  return sortEntries(entries, kind)
    .slice(0, limit)
    .map((entry) => toBulletinItem(entry, dependencies.applicationLogo, kind, nowMs))
}
