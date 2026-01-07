import { defineStore } from 'pinia'
import { type BalancesRequest, type BalanceOfRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { BALANCE_OF, BALANCES_OF_MEME } from 'src/graphql'
import { graphqlResult } from 'src/utils'
import { _Account, type Account } from '../account'
import { constants } from 'src/constant'

export const useMemeStore = defineStore('meme', {
  state: () => ({}),
  actions: {
    balanceOf(
      req: BalanceOfRequest,
      memeApplication: Account,
      done?: (error: boolean, balance?: string) => void,
    ) {
      const url = _Account.applicationUrl(constants.PROXY_URL, memeApplication)
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(
        apolloClient,
      )(() =>
        useQuery(
          BALANCE_OF,
          {
            owner: req.owner,
          },
          {
            fetchPolicy: 'network-only',
          },
        ),
      )

      onResult((res) => {
        const balance = graphqlResult.data(res, 'balanceOf') as string
        done?.(false, balance)
      })

      onError(() => {
        done?.(true)
      })
    },
    balances(
      req: BalancesRequest,
      memeApplication: Account,
      done?: (error: boolean, balances?: Record<string, string>) => void,
    ) {
      const url = _Account.applicationUrl(constants.PROXY_URL, memeApplication)
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(
        apolloClient,
      )(() =>
        useQuery(
          BALANCES_OF_MEME,
          {},
          {
            fetchPolicy: 'network-only',
          },
        ),
      )

      onResult((res) => {
        const balances = graphqlResult.data(res, 'balances') as Record<string, string>
        done?.(false, balances)
      })

      onError(() => {
        done?.(true)
      })
    },
  },
  getters: {},
})
