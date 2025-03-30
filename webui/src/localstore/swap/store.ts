import { defineStore } from 'pinia'
import { LatestTransactionsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { POOLS } from 'src/graphql'
import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { formalizeFloat, graphqlResult } from 'src/utils'
import { constants } from 'src/constant'
import { Transaction } from '../transaction'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useSwapStore = defineStore('swap', {
  state: () => ({
    pools: [] as Array<Pool>,
    selectedPool: undefined as unknown as Pool,
    selectedToken0: undefined as unknown as string,
    selectedToken1: undefined as unknown as string
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
        const _pool = {
          ...pool,
          token1: pool.token1 || constants.LINERA_NATIVE_ID
        } as Pool
        this.pools.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, _pool)
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
    price(): (token: string) => string | undefined {
      return (token: string) => {
        const pool = this.pools.find(
          (el) =>
            el.token0 === token && el.token1 === constants.LINERA_NATIVE_ID
        )
        return pool
          ? formalizeFloat.trimZeros(Number(pool?.token0Price).toFixed(8))
          : undefined
      }
    },
    getPool(): (token0: string, token1: string) => Pool | undefined {
      return (token0: string, token1: string) => {
        return this.pools.find(
          (el) =>
            (el.token0 === token0 && el.token1 === token1) ||
            (el.token1 === token0 && el.token0 === token1)
        )
      }
    },
    existPool(): (token0: string, token1: string) => boolean {
      return (token0: string, token1: string) => {
        return (
          this.pools.findIndex(
            (el) =>
              (el.token0 === token0 && el.token1 === token1) ||
              (el.token1 === token0 && el.token0 === token1)
          ) >= 0
        )
      }
    },
    existTokenPool(): (token: string) => boolean {
      return (token: string) => {
        return (
          this.pools.findIndex(
            (el) => el.token0 === token || el.token1 === token
          ) >= 0
        )
      }
    }
  }
})
