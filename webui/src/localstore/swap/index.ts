import { defineStore } from 'pinia'
import { LatestTransactionsRequest, Transaction } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { POOLS } from 'src/graphql'
import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { graphqlResult } from 'src/utils'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useSwapStore = defineStore('swap', {
  state: () => ({
    pools: [] as Array<Pool>
  }),
  actions: {
    getPools(
      req: LatestTransactionsRequest,
      done?: (error: boolean, rows?: Pool[]) => void
    ) {
      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            POOLS,
            {
              endpoint: 'swap'
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const chains = graphqlResult.data(res, 'pools') as Pool[]
        this.appendChains(chains)
        done?.(false, chains)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendChains(pools: Pool[]) {
      pools.forEach((pool) => {
        const index = this.pools.findIndex((el) => el.poolId === pool.poolId)
        this.pools.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, pool)
      })
    }
  },
  getters: {
    latestTransaction(): (token: string) => Transaction | undefined {
      return (token: string) => {
        return this.pools.find((el) => el.token0 === token)
          ?.latestTransaction as Transaction
      }
    },
    price(): (token: string) => string {
      return (token: string) => {
        return Number(
          this.pools.find((el) => el.token0 === token && !el.token1)
            ?.token1Price
        ).toFixed(8)
      }
    }
  }
})

export * from './types'
