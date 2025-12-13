import Dexie, { type Table } from 'dexie'
import { type Interval } from 'src/stores/kline/const'
import { type dbModel } from 'src/model'

export const dbKline = new Dexie('KLineDatabase') as Dexie & {
  klinePoints: Table<dbModel.KlinePoint, [string, string, Interval, number]>
  transactions: Table<dbModel._Transaction, [string, string, number, boolean]>
}

dbKline.version(11).stores({
  klinePoints: null,
  transactions: null,
  klinePointsV2:
    '++id, &[token0+token1+interval+timestamp], open, close, low, high, volume, timestamp',
  transactionsV2:
    '++id, &[token0+token1+transaction_id+token_reversed], &[created_timestamp+token0+token1+token_reversed], transaction_type, from_account, amount_0_in, amount_1_in, amount_0_out, amount_1_out, liquidity, created_at, created_timestamp, price, volume, direction',
})

Object.defineProperty(dbKline, 'transactions', {
  get() {
    return dbKline.table('transactionsV2')
  },
})

Object.defineProperty(dbKline, 'klinePoints', {
  get() {
    return dbKline.table('klinePointsV2')
  },
})
