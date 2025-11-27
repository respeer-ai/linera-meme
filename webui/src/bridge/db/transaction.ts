import { dbKline } from 'src/controller'
import { TransactionExt } from 'src/localstore/transaction/types'

export class Transaction {
  static bulkPut = async (
    token0: string,
    token1: string,
    transactions: TransactionExt[]
  ) => {
    const _transactions = transactions.map((transaction) => {
      return { ...transaction, token0, token1 }
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

  static transactions = async (
    token0: string,
    token1: string,
    tokenReversed: boolean,
    timestampBegin?: number,
    timestampEnd?: number,
    limit?: number
  ) => {
    const from = [timestampBegin ?? 0, token0, token1, !!tokenReversed]
    const to = [timestampEnd ?? Number.MAX_SAFE_INTEGER, token0, token1, !!tokenReversed]

    console.log(from, to)

    try {
      return await dbKline.transactions
        .where('[created_timestamp+token0+token1+token_reversed]')
        .between(from, to)
        .reverse()
        .limit(limit ?? 9999999)
        .toArray()
    } catch (e) {
      console.log('Failed query', e)
    }
  }
}
