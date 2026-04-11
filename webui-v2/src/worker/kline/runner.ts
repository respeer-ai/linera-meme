import { constants } from 'src/constant'
import { type Interval } from 'src/stores/kline/const'
import axios from 'axios'
import { type Point, type Points, type Transactions } from 'src/stores/kline/types'
import { type TransactionExt } from 'src/stores/transaction/types'
import { dbBridge } from 'src/bridge'
import { mergeKlinePoints } from './pointMerge'

export enum KlineEventType {
  FETCH_POINTS = 'FetchPoints',
  FETCH_TRANSACTIONS = 'FetchTransactions',

  FETCHED_POINTS = 'FetchedPoints',
  FETCHED_TRANSACTIONS = 'FetchedTransactions',

  LOAD_POINTS = 'LoadPoints',
  LOAD_TRANSACTIONS = 'LoadTransactions',

  LOADED_POINTS = 'LoadedPoints',
  LOADED_TRANSACTIONS = 'LoadedTransactions',

  NEW_POINTS = 'NewPoints',
  NEW_TRANSACTIONS = 'NewTransactions',

  SORT_POINTS = 'SortPoints',
  SORT_TRANSACTIONS = 'SortTransactions',

  SORTED_POINTS = 'SortedPoints',
  SORTED_TRANSACTIONS = 'SortedTransactions',

  Error = 'Error',
}

export interface BasePayload {
  token0: string
  token1: string
  poolId?: number
  poolApplication?: string
}

export interface FetchPointsPayload extends BasePayload {
  startAt: number
  endAt: number
  interval: Interval
  reverse: boolean
  requestId: number
}
export interface FetchTransactionsPayload extends BasePayload {
  startAt: number
  endAt: number
}
export interface FetchedPointsPayload extends BasePayload {
  points: Points
  interval: Interval
  reverse: boolean
  requestId: number
}
export interface FetchedTransactionsPayload extends BasePayload {
  startAt: number
  endAt: number
  transactions: TransactionExt[]
}
export interface LoadPointsPayload extends BasePayload {
  offset?: number
  limit?: number
  interval: Interval
  reverse: boolean
  timestampBegin?: number
  timestampEnd?: number
  requestId: number
}
export interface LoadTransactionsPayload extends BasePayload {
  tokenReversed: boolean
  timestampBegin?: number
  timestampEnd?: number
  limit: number
}
export interface LoadedPointsPayload extends BasePayload {
  offset: number
  limit: number
  interval: string
  points: Point[]
  reverse: boolean
  timestampBegin?: number
  timestampEnd?: number
  requestId: number
}
export interface LoadedTransactionsPayload extends BasePayload {
  timestampBegin?: number
  timestampEnd?: number
  transactions: TransactionExt[]
}
export type NewPointsPayload = Map<Interval, Points[]>
export type NewTransactionsPayload = Transactions[]
export interface SortPointsPayload extends BasePayload {
  originPoints: Point[]
  newPoints: Point[]
  keepCount: number
  reverse: boolean
  reason: unknown
  requestId: number
}
export interface SortedPointsPayload extends BasePayload {
  points: Point[]
  reverse: boolean
  reason: unknown
  requestId: number
}
export interface SortTransactionsPayload extends BasePayload {
  tokenReversed: boolean
  originTransactions: TransactionExt[]
  newTransactions: TransactionExt[]
  keepCount: number
  reverse: boolean
  reason: unknown
}
export interface SortedTransactionsPayload extends BasePayload {
  transactions: TransactionExt[]
  reason: unknown
}

export interface KlineEvent {
  type: KlineEventType
  payload:
    | FetchPointsPayload
    | FetchTransactionsPayload
    | LoadPointsPayload
    | LoadTransactionsPayload
    | FetchedPointsPayload
    | FetchedTransactionsPayload
    | LoadedPointsPayload
    | LoadedTransactionsPayload
    | NewPointsPayload
    | NewTransactionsPayload
    | SortPointsPayload
    | SortTransactionsPayload
    | SortedPointsPayload
    | SortedTransactionsPayload
}

export const buildKlineRequestTraceId = ({
  token0,
  token1,
  interval,
  startAt,
  endAt,
  reverse,
  requestId,
}: FetchPointsPayload): string =>
  `${requestId}:${interval}:${reverse ? 'reverse' : 'forward'}:${startAt}:${endAt}:${token0.slice(0, 8)}:${token1.slice(0, 8)}`

export const appendKlineTraceParams = (url: string, traceId: string, sentAtMs: number): string => {
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}request_id=${encodeURIComponent(traceId)}&client_sent_at_ms=${sentAtMs}`
}

export class KlineRunner {
  static storePoints = async (
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
    interval: Interval,
    points: Points,
    offset: number,
    count: number,
  ) => {
    if (offset >= points.points.length) return

    await dbBridge.Kline.bulkPut(
      token0,
      token1,
      poolId,
      poolApplication,
      interval,
      points.points.slice(offset, offset + count),
    )

    setTimeout(() => {
      void KlineRunner.storePoints(
        token0,
        token1,
        poolId,
        poolApplication,
        interval,
        points,
        offset + count,
        count,
      )
    })
  }

  static bulkStorePoints = (
    token0: string,
    token1: string,
    poolId: number,
    poolApplication: string,
    interval: Interval,
    points: Points,
  ) => {
    void KlineRunner.storePoints(token0, token1, poolId, poolApplication, interval, points, 0, 20)
  }

  static handleFetchPoints = async (payload: FetchPointsPayload) => {
    const {
      token0,
      token1,
      poolId,
      poolApplication,
      startAt,
      endAt,
      interval,
      reverse,
      requestId,
    } = payload
    if (poolId === undefined || !poolApplication) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: 'Missing pool identity for kline fetch',
      })
      return
    }
    const traceId = buildKlineRequestTraceId(payload)

    const url = new URL(
      constants.formalizeSchema(
        `${constants.KLINE_HTTP_URL}/points/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}/interval/${interval}`,
      ),
    )
    url.searchParams.set('pool_id', String(poolId))
    url.searchParams.set('pool_application', poolApplication)

    try {
      const sentAtMs = Date.now()
      const tracedUrl = appendKlineTraceParams(url.toString(), traceId, sentAtMs)
      console.log('[KlineRunner] fetch points start', { traceId, url: tracedUrl, sentAtMs })
      const res = await axios.get(tracedUrl)
      console.log('[KlineRunner] fetch points done', {
        traceId,
        status: res.status,
        durationMs: Date.now() - sentAtMs,
      })

      const points = res.data as Points
      points.end_at = endAt

      KlineRunner.bulkStorePoints(token0, token1, poolId, poolApplication, interval, points)

      self.postMessage({
        type: KlineEventType.FETCHED_POINTS,
        payload: {
          token0,
          token1,
          poolId,
          poolApplication,
          points,
          interval,
          reverse,
          requestId,
        },
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e,
      })
    }
  }

  static storeTransactions = async (
    token0: string,
    token1: string,
    transactions: TransactionExt[],
    offset: number,
    count: number,
  ) => {
    if (offset >= transactions.length) return

    await dbBridge.Transaction.bulkPut(token0, token1, transactions.slice(offset, offset + count))

    setTimeout(() => {
      void KlineRunner.storeTransactions(token0, token1, transactions, offset + count, count)
    })
  }

  static bulkStoreTransactions = (
    token0: string,
    token1: string,
    transactions: TransactionExt[],
  ) => {
    void KlineRunner.storeTransactions(token0, token1, transactions, 0, 20)
  }

  static handleFetchTransactions = async (payload: FetchTransactionsPayload) => {
    const { token0, token1, startAt, endAt } = payload

    const url = constants.formalizeSchema(
      token0 && token1
        ? `${constants.KLINE_HTTP_URL}/transactions/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}`
        : `${constants.KLINE_HTTP_URL}/transactions/start_at/${startAt}/end_at/${endAt}`,
    )

    try {
      const res = await axios.get(url)
      const transactions = res.data as TransactionExt[]

      KlineRunner.bulkStoreTransactions(token0, token1, transactions)

      self.postMessage({
        type: KlineEventType.FETCHED_TRANSACTIONS,
        payload: {
          token0,
          token1,
          startAt,
          endAt,
          transactions,
        },
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: JSON.stringify(e),
      })
    }
  }

  static handleLoadPoints = async (payload: LoadPointsPayload) => {
    const {
      token0,
      token1,
      poolId,
      poolApplication,
      offset,
      limit,
      interval,
      reverse,
      timestampBegin,
      timestampEnd,
      requestId,
    } = payload
    if (poolId === undefined || !poolApplication) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: 'Missing pool identity for kline cache load',
      })
      return
    }

    try {
      const points = await dbBridge.Kline.points(
        token0,
        token1,
        poolId,
        poolApplication,
        interval,
        offset,
        limit,
        reverse,
        timestampBegin,
        timestampEnd,
      )

      self.postMessage({
        type: KlineEventType.LOADED_POINTS,
        payload: {
          token0,
          token1,
          poolId,
          poolApplication,
          offset,
          limit,
          interval,
          points,
          reverse,
          timestampBegin,
          timestampEnd,
          requestId,
        },
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e,
      })
    }
  }

  static handleLoadTransactions = async (payload: LoadTransactionsPayload) => {
    const { token0, token1, timestampBegin, timestampEnd, tokenReversed, limit } = payload

    try {
      const transactions = await dbBridge.Transaction.transactions(
        token0,
        token1,
        tokenReversed,
        timestampBegin,
        timestampEnd,
        limit,
      )

      self.postMessage({
        type: KlineEventType.LOADED_TRANSACTIONS,
        payload: {
          token0,
          token1,
          timestampBegin,
          timestampEnd,
          transactions,
        },
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e,
      })
    }
  }

  static handleNewPoints = (payload: NewPointsPayload) => {
    const points = payload

    points.forEach((_points, interval) => {
      _points.forEach((__points) => {
        // Timestamp is already converted, not good but work
        KlineRunner.bulkStorePoints(
          __points.token_0,
          __points.token_1,
          __points.pool_id ?? 0,
          __points.pool_application ?? 'unknown',
          interval,
          __points,
        )
      })
    })
  }

  static handleNewTransactions = (payload: NewTransactionsPayload) => {
    const transactions = payload

    transactions.forEach((_transactions) => {
      KlineRunner.bulkStoreTransactions(
        _transactions.token_0,
        _transactions.token_1,
        _transactions.transactions,
      )
    })
  }

  static handleSortPoints = (payload: SortPointsPayload) => {
    const {
      token0,
      token1,
      poolId,
      poolApplication,
      originPoints,
      newPoints,
      reason,
      keepCount,
      reverse,
      requestId,
    } = payload

    const _points = mergeKlinePoints({
      originPoints,
      newPoints,
      reason: reason as { reason?: string },
    })
    const _keepCount = keepCount < 0 ? _points.length : keepCount

    self.postMessage({
      type: KlineEventType.SORTED_POINTS,
      payload: {
        token0,
        token1,
        poolId,
        poolApplication,
        points: _points.slice(
          reverse ? 0 : Math.max(_points.length - _keepCount, 0),
          reverse ? _keepCount : _points.length,
        ),
        reverse,
        reason,
        requestId,
      },
    })
  }

  static handleSortTransactions = (payload: SortTransactionsPayload) => {
    const {
      token0,
      token1,
      originTransactions,
      newTransactions,
      keepCount,
      reverse,
      reason,
      tokenReversed,
    } = payload

    let _tokenReversed = tokenReversed

    if (!token0 || !token1) _tokenReversed = false

    newTransactions.forEach((transaction) => {
      const index = originTransactions.findIndex(
        (el) =>
          el.transaction_id === transaction.transaction_id &&
          el.token_reversed === transaction.token_reversed,
      )
      return index >= 0
        ? (originTransactions[index] = transaction)
        : originTransactions.push(transaction)
    })

    const transactions = originTransactions.filter((el) =>
      _tokenReversed ? el.token_reversed == 1 : el.token_reversed == 0,
    )
    const _transactions = transactions.sort((p1, p2) =>
      reverse ? p2.created_at - p1.created_at : p1.created_at - p2.created_at,
    )
    const _keepCount = keepCount < 0 ? _transactions.length : keepCount

    self.postMessage({
      type: KlineEventType.SORTED_TRANSACTIONS,
      payload: {
        token0,
        token1,
        transactions: _transactions.slice(
          reverse ? 0 : Math.max(_transactions.length - _keepCount, 0),
          reverse ? _keepCount : _transactions.length,
        ),
        reason,
      },
    })
  }
}
