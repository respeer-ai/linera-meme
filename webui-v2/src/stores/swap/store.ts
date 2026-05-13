import { defineStore } from 'pinia'
import { type PoolsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { POOLS } from 'src/graphql'
import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { formalizeFloat, graphqlResult } from 'src/utils'
import { constants } from 'src/constant'
import { Subscription } from 'src/subscription'
import { poolIdentityKey } from './poolIdentity'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useSwapStore = defineStore('swap', {
  state: () => ({
    pools: [] as Array<Pool>,
    buyToken: undefined as unknown as string,
    sellToken: undefined as unknown as string,
    subscription: undefined as unknown as Subscription,
    blockHash: undefined as unknown as string,
  }),
  actions: {
    initializeSwap() {
      this.subscription = new Subscription(
        constants.SWAP_URL,
        constants.SWAP_WS_URL,
        constants.chainId(constants.APPLICATION_URLS.SWAP) as string,
        (height: number, hash: string) => {
          console.log(`New block height ${height} hash ${hash} on swap chain`)
          this.blockHash = hash
        },
      )
    },
    finalizeProxy() {
      this.subscription?.unsubscribe()
    },
    getPools(req: PoolsRequest, done?: (error: boolean, rows?: Pool[]) => void) {
      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(
        apolloClient,
      )(() =>
        useQuery(
          POOLS,
          {
            endpoint: 'swap',
          },
          {
            fetchPolicy: 'network-only',
          },
        ),
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
        const identityKey = poolIdentityKey(pool)
        const index = this.pools.findIndex((el) => poolIdentityKey(el) === identityKey)
        const _pool = {
          ...pool,
          token1: (pool.token1 as string) || constants.LINERA_NATIVE_ID,
        } as Pool
        this.pools.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, _pool)
      })
    },
  },
  getters: {
    price(): (token: string) => string | undefined {
      return (token: string) => {
        const pool = this.pools.find(
          (el) => el.token0 === token && el.token1 === constants.LINERA_NATIVE_ID,
        )
        return pool ? formalizeFloat.trimZeros(Number(pool?.token0Price).toFixed(8)) : undefined
      }
    },
    getPool(): (token0: string, token1: string) => Pool | undefined {
      return (token0: string, token1: string) => {
        return this.pools.find(
          (el) =>
            (el.token0 === token0 && el.token1 === token1) ||
            (el.token1 === token0 && el.token0 === token1),
        )
      }
    },
    existPool(): (token0: string, token1: string) => boolean {
      return (token0: string, token1: string) => {
        return (
          this.pools.findIndex(
            (el) =>
              (el.token0 === token0 && el.token1 === token1) ||
              (el.token1 === token0 && el.token0 === token1),
          ) >= 0
        )
      }
    },
    existTokenPool(): (token: string) => boolean {
      return (token: string) => {
        return this.pools.findIndex((el) => el.token0 === token || el.token1 === token) >= 0
      }
    },
  },
})
