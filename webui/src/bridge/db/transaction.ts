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
    offset: number,
    limit: number
  ) => {
    return await dbKline.transactions
      .orderBy('created_at')
      .reverse()
      .filter((obj) => obj.token0 === token0 && obj.token1 === token1)
      .offset(offset)
      .limit(limit)
      .toArray()
  }
}
