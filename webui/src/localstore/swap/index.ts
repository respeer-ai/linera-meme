import { defineStore } from 'pinia'
import { LatestTransactionsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { LATEST_TRANSACTIONS } from 'src/graphql'
import { TransactionExt } from 'src/__generated__/graphql/swap/graphql'
import { graphqlResult } from 'src/utils'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useSwapStore = defineStore('swap', {
  state: () => ({
    transactions: [] as Array<TransactionExt>
  }),
  actions: {
    latestTransactions(
      req: LatestTransactionsRequest,
      done?: (error: boolean, rows?: TransactionExt[]) => void
    ) {
      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            LATEST_TRANSACTIONS,
            {
              endpoint: 'swap'
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const chains = graphqlResult.data(
          res,
          'latestTransactions'
        ) as TransactionExt[]
        this.appendChains(chains)
        done?.(false, chains)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendChains(chains: TransactionExt[]) {
      chains.forEach((transaction) => {
        const index = this.transactions.findIndex(
          (el) =>
            el.token0 === transaction.token0 && el.token1 === transaction.token1
        )
        this.transactions.splice(
          index >= 0 ? index : 0,
          index >= 0 ? 1 : 0,
          transaction
        )
      })
    }
  },
  getters: {
    latestTransaction(): (token: string) => TransactionExt | undefined {
      return (token: string) => {
        return this.transactions.find((el) => el.token0 === token)
      }
    }
  }
})

export * from './types'
