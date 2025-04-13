import { constants } from 'src/constant'
import { Interval } from 'src/localstore/kline/const'
import axios from 'axios'
import { Point, Points } from 'src/localstore/kline/types'
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
}

export class KlineRunner {
  static handleFetchPoints = async (payload: FetchPointsPayload) => {
    const { token0, token1, startAt, endAt, interval } = payload

    const url = constants.formalizeSchema(
      `${constants.KLINE_HTTP_URL}/points/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}/interval/${interval}`
    )

    try {
      const res = await axios.get(url)

      const points = res.data as Points
      points.end_at = endAt

      await dbBridge.Kline.bulkPut(
        token0,
        token1,
        interval,
        points.points.map((el) => {
          return {
            ...el,
            timestamp: Date.parse(el.timestamp as unknown as string)
          }
        })
      )

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

      await dbBridge.Transaction.bulkPut(token0, token1, transactions)

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
}
