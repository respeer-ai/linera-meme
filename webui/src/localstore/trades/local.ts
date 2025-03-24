import { defineStore } from 'pinia'
import { API, Transaction, GetTransactionsForLineResponse } from './types'
import { doActionWithError } from '../action'
import { NotifyType } from '../notification'
import { useHostStore } from '../host'

export const useTradesStore = defineStore('useTradesStore', {
  state: () => ({
    NeedInitTxTable: true,
    SelectedPoolID: null as number | null,
    OriginalTxID: 0 as number,
    Transactions: [] as Transaction[],
    RefreshTableHistoryLock: false,
    MaxTransactions: 1000,
    ResetTableViewLock: 0
  }),
  actions: {
    refreshNewTransactions (done?: (error: boolean, rows: Transaction[]) => void) {
      if (this.SelectedPoolID === null || this.SelectedPoolID < 0) {
        return
      }
      doActionWithError<unknown, GetTransactionsForLineResponse>(
        useHostStore().formalizeKlinePath(API.GetTransactionsForLine),
        {
          Limit: 20,
          Offset: 0,
          OriginalTxID: this.OriginalTxID,
          PoolID: this.SelectedPoolID
        },
        {
          Error: {
            Title: 'Get Transactions',
            Message: 'Failed to fetch transactions',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetTransactionsForLineResponse): void => {
          if (this.OriginalTxID === 0) {
            this.OriginalTxID = resp.OriginalTxID
          }
          if (resp.Transactions.length) {
            this._refreshTableTransactions(resp.Transactions, true)
            if (this.Transactions.length > this.MaxTransactions) {
              this.Transactions.splice(0, this.Transactions.length - this.MaxTransactions)
            }
          }

          done?.(false, resp.Transactions)
        }, () => {
          done?.(true, [])
        }
      )
    },
    refreshHistoryTransactions (done?: (error: boolean, rows: Transaction[]) => void) {
      if (this.SelectedPoolID === null || this.SelectedPoolID < 0) {
        return
      }
      if (this.Transactions.length >= this.MaxTransactions) {
        return
      }
      if (this.RefreshTableHistoryLock) {
        return
      }
      this.RefreshTableHistoryLock = true
      doActionWithError<unknown, GetTransactionsForLineResponse>(
        useHostStore().formalizeKlinePath(API.GetTransactionsForLine),
        {
          Limit: -20,
          Offset: -this.Transactions.length,
          OriginalTxID: this.OriginalTxID,
          PoolID: this.SelectedPoolID
        },
        {
          Error: {
            Title: 'Get Transaction Histories',
            Message: 'Failed to get transactions histories',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetTransactionsForLineResponse): void => {
          if (this.OriginalTxID === 0) {
            this.OriginalTxID = resp.OriginalTxID
          }

          if (resp.Transactions.length > 0) {
            this._refreshTableTransactions(resp.Transactions, false)
          }

          done?.(false, resp.Transactions)
        }, () => {
          done?.(true, [])
        }
      )

      setTimeout(() => {
        this.RefreshTableHistoryLock = false
      }, 300)
    },
    _refreshTableTransactions (infos: Transaction[], unshift: boolean) {
      for (let i = 0; i < infos.length; i++) {
        if (unshift) {
          this.Transactions.unshift(infos[i])
        } else {
          this.Transactions.push(infos[i])
        }
      }
      this.OriginalTxID = this.Transactions[0].TransactionID - 0 + 1
    }
  }
})
