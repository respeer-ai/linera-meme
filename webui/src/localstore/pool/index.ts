import { defineStore } from 'pinia'
import { LatestTransactionsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { LATEST_TRANSACTIONS } from 'src/graphql'
import { graphqlResult } from 'src/utils'
import { Transaction } from '../transaction'
import { _Account, Account } from '../account'

export const usePoolStore = defineStore('pool', {
  state: () => ({
    transactions: new Map<number, Array<Transaction>>()
  }),
  actions: {
    latestTransactions(
      req: LatestTransactionsRequest,
      poolId: number,
      poolApplication: Account,
      done?: (error: boolean, rows?: Transaction[]) => void
    ) {
      const url = _Account.applicationUrl(
        'api.lineraswap.fun',
        'swap',
        poolApplication
      )
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            LATEST_TRANSACTIONS,
            {
              startId: req.startId
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const transactions = graphqlResult.data(
          res,
          'latestTransactions'
        ) as Transaction[]
        this.appendTransactions(poolId, transactions)
        done?.(false, transactions)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendTransactions(poolId: number, transactions: Transaction[]) {
      const _transactions = [ ...(this.transactions.get(poolId) || []) ]
      transactions.forEach((transaction) => {
        const index = _transactions.findIndex(
          (el) => el.transactionId === transaction.transactionId
        )
        _transactions.splice(
          index >= 0 ? index : 0,
          index >= 0 ? 1 : 0,
          { ...transaction }
        )
      })
      this.transactions.set(poolId, transactions)
    }
  },
  getters: {
    nextStartId(): (poolId: number) => number {
      return (poolId: number) => {
        return this.transactions.get(poolId)?.at(-1)?.transactionId || 0
      }
    },
    _transactions(): (poolId: number) => Transaction[] {
      return (poolId: number) => {
        return [...(this.transactions.get(poolId) || [])].reverse()
      }
    }
  }
})

export * from './types'
