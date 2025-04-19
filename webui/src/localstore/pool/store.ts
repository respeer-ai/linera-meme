import { defineStore } from 'pinia'
import { constants } from '../../constant'
import {
  LiquidityAmount,
  CalculateLiquidityAmountPairRequest,
  LatestTransactionsRequest,
  LiquidityRequest
} from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import {
  CALCULATE_AMOUNT_LIQUIDITY,
  LATEST_TRANSACTIONS,
  LIQUIDITY
} from 'src/graphql'
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
        constants.SWAP_HOST,
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
      const _transactions = [...(this.transactions.get(poolId) || [])]
      transactions.forEach((transaction) => {
        const index = _transactions.findIndex(
          (el) => el.transactionId === transaction.transactionId
        )
        _transactions.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, {
          ...transaction
        })
      })
      this.transactions.set(poolId, transactions)
    },
    calculateLiquidityAmountPair(
      req: CalculateLiquidityAmountPairRequest,
      poolApplication: Account,
      done?: (error: boolean, liquidity?: LiquidityAmount) => void
    ) {
      const url = _Account.applicationUrl(
        constants.SWAP_HOST,
        poolApplication
      )
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            CALCULATE_AMOUNT_LIQUIDITY,
            {
              amount0Desired: req.amount0Desired,
              amount1Desired: req.amount1Desired
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const liquidity = graphqlResult.data(
          res,
          'calculateAmountLiquidity'
        ) as LiquidityAmount
        done?.(false, liquidity)
      })

      onError(() => {
        done?.(true)
      })
    },
    liquidity(
      req: LiquidityRequest,
      poolApplication: Account,
      done?: (error: boolean, liquidity?: LiquidityAmount) => void
    ) {
      const url = _Account.applicationUrl(
        constants.SWAP_HOST,
        poolApplication
      )
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            LIQUIDITY,
            {
              owner: req.owner
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const liquidity = graphqlResult.data(
          res,
          'liquidity'
        ) as LiquidityAmount
        done?.(false, liquidity)
      })

      onError(() => {
        done?.(true)
      })
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
