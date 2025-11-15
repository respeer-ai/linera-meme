import { defineStore } from 'pinia'
import { GetChainsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { MEME_APPLICATIONS } from 'src/graphql'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { graphqlResult } from 'src/utils'
import { Account } from '../account'
import { constants } from 'src/constant'
import { Subscription } from 'src/subscription'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useProxyStore = defineStore('proxy', {
  state: () => ({
    chains: [] as Array<Chain>,
    subscription: undefined as unknown as Subscription,
    blockHash: undefined as unknown as string
  }),
  actions: {
    initializeProxy() {
      this.subscription = new Subscription(
        constants.PROXY_URL,
        constants.PROXY_WS_URL,
        constants.chainId(constants.APPLICATION_URLS.PROXY) as string,
        (hash: string) => {
          this.blockHash = hash
        }
      )
    },
    finalizeProxy() {
      this.subscription?.unsubscribe()
    },
    onError(e: Event) {
      console.log(`Proxy error: ${JSON.stringify(e)}`)
    },
    getApplications(
      req: GetChainsRequest,
      done?: (error: boolean, rows?: Chain[]) => void
    ) {
      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            MEME_APPLICATIONS,
            {
              endpoint: 'proxy'
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const chains = graphqlResult.data(res, 'memeApplications') as Chain[]
        this.appendChains(chains)
        done?.(false, chains)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendChains(chains: Chain[]) {
      chains.forEach((chain) => {
        const index = this.chains.findIndex(
          (el) => el.chainId === chain.chainId
        )
        this.chains.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, chain)
      })
    }
  },
  getters: {
    chain(): (token: string) => Chain | undefined {
      return (token: string) => {
        return this.chains.find((el) => el.token === token)
      }
    },
    application(): (token: string) => Account | undefined {
      return (token: string) => {
        const chain = this.chains.find((el) => el.token === token)
        return {
          chain_id: chain?.chainId as string,
          owner: chain?.token as string
        }
      }
    }
  }
})
