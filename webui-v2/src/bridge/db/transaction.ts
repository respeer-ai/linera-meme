import { dbKline } from 'src/controller'
import { type TransactionExt } from 'src/stores/transaction/types'

export class Transaction {
  static bulkPut = async (token0: string, token1: string, transactions: TransactionExt[]) => {
    const _transactions = transactions.map((transaction) => {
      return {
        ...transaction,
        token0,
        token1,
        token_reversed: transaction.token_reversed ? 1 : 0,
      }
    })
    const traceFunc = console.trace
    console.trace = () => {
      // DO NOTHING
    }
    try {
      await dbKline.transactions.bulkPut(_transactions)
    } catch {
      // DO NOTHING
    }
    console.trace = traceFunc
  }

  static transactionsCount = async (token0: string, token1: string, tokenReversed: number) => {
    const from = [0, token0, token1, tokenReversed]
    const to = [Number.MAX_SAFE_INTEGER, token0, token1, tokenReversed]

    try {
      return await dbKline.transactions
        .where('[created_timestamp+token0+token1+token_reversed]')
        .between(from, to)
        .count()
    } catch (e) {
      console.log('Failed query', e)
    }
  }

  static transactions = async (
    token0: string,
    token1: string,
    tokenReversed: boolean,
    timestampBegin?: number,
    timestampEnd?: number,
    limit?: number,
  ) => {
    const startAt = timestampBegin ? timestampBegin * 1000 : 0
    const endAt = timestampEnd ? timestampEnd * 1000 : Number.MAX_SAFE_INTEGER

    const _startAt = startAt > endAt ? endAt : startAt
    const _endAt = startAt > endAt ? startAt : endAt

    const from =
      token0 && token1
        ? [_startAt, token0, token1, tokenReversed ? 1 : 0]
        : [_startAt, tokenReversed ? 1 : 0]
    const to =
      token0 && token1
        ? [_endAt, token0, token1, tokenReversed ? 1 : 0]
        : [_endAt, tokenReversed ? 1 : 0]

    try {
      return await dbKline.transactions
        .where(
          token0 && token1
            ? '[created_timestamp+token0+token1+token_reversed]'
            : '[created_timestamp+token_reversed]',
        )
        .between(from, to)
        .reverse()
        .limit(limit ? limit * 2 : 999999)
        .toArray()
    } catch (e) {
      console.log('Failed query', e)
    }
  }
}
