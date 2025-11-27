import Dexie, { Table } from 'dexie'
import { Interval } from 'src/localstore/kline/const'
import { dbModel } from 'src/model'

export const dbKline = new Dexie('KLineDatabase') as Dexie & {
  klinePoints: Table<dbModel.KlinePoint, [string, string, Interval, number]>
  transactions: Table<dbModel._Transaction, [string, string, number, boolean]>
}

dbKline.version(6).stores({
  klinePoints:
    '++id, &[token0+token1+interval+timestamp], open, close, low, high, volume, timestamp',
  transactions:
    '++id, &[token0+token1+transaction_id+token_reversed], &[created_timestamp+token0+token1+token_reversed], transaction_type, from_account, amount_0_in, amount_1_in, amount_0_out, amount_1_out, liquidity, created_at, created_timestamp, price, volume, direction'
})
