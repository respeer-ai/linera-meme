import { defineStore } from 'pinia'
import { GetChainsRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { MEME_APPLICATIONS } from 'src/graphql'
import { Chain } from 'src/__generated__/graphql/proxy/graphql'
import { graphqlResult } from 'src/utils'
import { Account } from '../account'
import { _WebSocket, Notification } from 'src/websocket'
import { constants } from 'src/constant'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useProxyStore = defineStore('proxy', {
  state: () => ({
    chains: [] as Array<Chain>,
    websocket: undefined as unknown as _WebSocket
  }),
  actions: {
    initializeProxy() {
      this.websocket = new _WebSocket(constants.PROXY_HOST)
      this.websocket.withOnMessage((notification) =>
        this.onMessage(notification)
      )
      this.websocket.withOnError((e) => this.onError(e))
    },
    onMessage(notification: Notification) {
      if (notification.notification === 'NewBlock') {
        this.getApplications({})
      }
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
          chainId: chain?.chainId as string,
          owner: chain?.token as string
        }
      }
    }
  }
})
