import { constants } from 'src/constant'
import { Interval } from 'src/localstore/kline/const'
import axios from 'axios'
import { Point, Points, Transactions } from 'src/localstore/kline/types'
import { TransactionExt } from 'src/localstore/transaction/types'
import { dbBridge } from 'src/bridge'

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

  Error = 'Error'
}

export interface BasePayload {
  token0: string
  token1: string
}

export interface FetchPointsPayload extends BasePayload {
  startAt: number
  endAt: number
  interval: Interval
}
export interface FetchTransactionsPayload extends BasePayload {
  startAt: number
  endAt: number
}
export type FetchedPointsPayload = Points
export interface FetchedTransactionsPayload extends BasePayload {
  startAt: number
  endAt: number
  transactions: TransactionExt[]
}
export interface LoadPointsPayload extends BasePayload {
  offset: number
  limit: number
  interval: Interval
}
export interface LoadTransactionsPayload extends BasePayload {
  offset: number
  limit: number
}
export interface LoadedPointsPayload extends BasePayload {
  offset: number
  limit: number
  interval: string
  points: Point[]
}
export interface LoadedTransactionsPayload extends BasePayload {
  offset: number
  limit: number
  transactions: TransactionExt[]
}
export type NewPointsPayload = Map<Interval, Points[]>
export type NewTransactionsPayload = Transactions[]
export interface SortPointsPayload {
  originPoints: Point[]
  newPoints: Point[]
  keepCount: number
  reverse: boolean
  reason: unknown
}
export interface SortedPointsPayload {
  points: Point[]
  reason: unknown
}
export interface SortTransactionsPayload {
  originTransactions: TransactionExt[]
  newTransactions: TransactionExt[]
  keepCount: number
  reverse: boolean
  reason: unknown
}
export interface SortedTransactionsPayload {
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

export class KlineRunner {
  static storePoints = async (
    token0: string,
    token1: string,
    interval: Interval,
    points: Points,
    offset: number,
    count: number
  ) => {
    if (offset >= points.points.length) return

    await dbBridge.Kline.bulkPut(
      token0,
      token1,
      interval,
      points.points.slice(offset, offset + count)
    )

    setTimeout(() => {
      void KlineRunner.storePoints(
        token0,
        token1,
        interval,
        points,
        offset + count,
        count
      )
    })
  }

  static bulkStorePoints = (
    token0: string,
    token1: string,
    interval: Interval,
    points: Points
  ) => {
    void KlineRunner.storePoints(token0, token1, interval, points, 0, 20)
  }

  static handleFetchPoints = async (payload: FetchPointsPayload) => {
    const { token0, token1, startAt, endAt, interval } = payload

    const url = constants.formalizeSchema(
      `${constants.KLINE_HTTP_URL}/points/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}/interval/${interval}`
    )

    try {
      const res = await axios.get(url)

      const points = res.data as Points
      points.end_at = endAt
      points.points = points.points.map((el) => {
        return {
          ...el,
          timestamp: Math.floor(Date.parse(el.timestamp as unknown as string))
        }
      })

      KlineRunner.bulkStorePoints(token0, token1, interval, points)

      await dbBridge.Kline.bulkPut(token0, token1, interval, points.points)

      self.postMessage({
        type: KlineEventType.FETCHED_POINTS,
        payload: points
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e
      })
    }
  }

  static storeTransactions = async (
    token0: string,
    token1: string,
    transactions: TransactionExt[],
    offset: number,
    count: number
  ) => {
    if (offset >= transactions.length) return

    await dbBridge.Transaction.bulkPut(
      token0,
      token1,
      transactions.slice(offset, offset + count)
    )

    setTimeout(() => {
      void KlineRunner.storeTransactions(
        token0,
        token1,
        transactions,
        offset + count,
        count
      )
    })
  }

  static bulkStoreTransactions = (
    token0: string,
    token1: string,
    transactions: TransactionExt[]
  ) => {
    void KlineRunner.storeTransactions(token0, token1, transactions, 0, 20)
  }

  static handleFetchTransactions = async (
    payload: FetchTransactionsPayload
  ) => {
    const { token0, token1, startAt, endAt } = payload

    const url = constants.formalizeSchema(
      `${constants.KLINE_HTTP_URL}/transactions/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}`
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
          transactions
        }
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e
      })
    }
  }

  static handleLoadPoints = async (payload: LoadPointsPayload) => {
    const { token0, token1, offset, limit, interval } = payload

    try {
      const points = await dbBridge.Kline.points(
        token0,
        token1,
        interval,
        offset,
        limit
      )

      self.postMessage({
        type: KlineEventType.LOADED_POINTS,
        payload: {
          token0,
          token1,
          offset,
          limit,
          interval,
          points
        }
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e
      })
    }
  }

  static handleLoadTransactions = async (payload: LoadTransactionsPayload) => {
    const { token0, token1, offset, limit } = payload

    try {
      const transactions = await dbBridge.Transaction.transactions(
        token0,
        token1,
        offset,
        limit
      )

      self.postMessage({
        type: KlineEventType.LOADED_TRANSACTIONS,
        payload: {
          token0,
          token1,
          offset,
          limit,
          transactions
        }
      })
    } catch (e) {
      self.postMessage({
        type: KlineEventType.Error,
        payload: e
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
          interval,
          __points
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
        _transactions.transactions
      )
    })
  }

  static handleSortPoints = (payload: SortPointsPayload) => {
    let { originPoints, newPoints, reason, keepCount, reverse } = payload

    newPoints.forEach((point) => {
      const index = originPoints.findIndex(
        (el) => el.timestamp === point.timestamp
      )
      index >= 0 ? (originPoints[index] = point) : originPoints.push(point)
    })

    const points = originPoints
    const _points = points.sort((p1, p2) =>
      reverse ? p2.timestamp - p1.timestamp : p1.timestamp - p2.timestamp
    )
    keepCount = keepCount < 0 ? _points.length : keepCount

    self.postMessage({
      type: KlineEventType.SORTED_POINTS,
      payload: {
        points: _points.slice(
          reverse ? 0 : Math.max(_points.length - keepCount, 0),
          reverse ? keepCount : _points.length
        ),
        reason
      }
    })
  }

  static handleSortTransactions = (payload: SortTransactionsPayload) => {
    let { originTransactions, newTransactions, keepCount, reverse, reason } =
      payload

    newTransactions.forEach((point) => {
      const index = originTransactions.findIndex(
        (el) => el.created_at === point.created_at
      )
      index >= 0
        ? (originTransactions[index] = point)
        : originTransactions.push(point)
    })

    const transactions = originTransactions
    const _transactions = transactions.sort((p1, p2) =>
      reverse ? p2.created_at - p1.created_at : p1.created_at - p2.created_at
    )
    keepCount = keepCount < 0 ? _transactions.length : keepCount

    self.postMessage({
      type: KlineEventType.SORTED_TRANSACTIONS,
      payload: {
        transactions: _transactions.slice(
          reverse ? 0 : Math.max(_transactions.length - keepCount, 0),
          payload.reverse ? keepCount : _transactions.length
        ),
        reason
      }
    })
  }
}
