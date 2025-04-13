import { constants } from 'src/constant'
import { Interval } from 'src/localstore/kline/const'
import axios from 'axios'
import { Points } from 'src/localstore/kline/types'
import { TransactionExt } from 'src/localstore/transaction/types'

export enum KlineEventType {
  FETCH_POINTS = 'FetchPoints',
  FETCH_TRANSACTIONS = 'FetchTransactions',

  FETCHED_POINTS = 'FetchedPoints',
  FETCHED_TRANSACTIONS = 'FetchedTransactions',

  Error = 'Error'
}

export interface BasePayload {
  token0: string
  token1: string
  startAt: number
  endAt: number
}

export interface FetchPointsPayload extends BasePayload {
  interval: Interval
}
export type FetchTransactionsPayload = BasePayload
export type FetchedPointsPayload = Points
export interface FetchedTransactionsPayload extends BasePayload {
  transactions: TransactionExt[]
}

export interface KlineEvent {
  type: KlineEventType
  payload: FetchPointsPayload | FetchTransactionsPayload | FetchedPointsPayload
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

  static handleFetchTransactions = async (payload: FetchTransactionsPayload) => {
    const { token0, token1, startAt, endAt } = payload

    const url = constants.formalizeSchema(
      `${constants.KLINE_HTTP_URL}/transactions/token0/${token0}/token1/${token1}/start_at/${startAt}/end_at/${endAt}`
    )

    try {
      const res = await axios.get(url)
      const transactions = res.data as TransactionExt[]

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
}
