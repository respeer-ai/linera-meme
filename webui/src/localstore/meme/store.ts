import { defineStore } from 'pinia'
import { BalanceOfRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { BALANCE_OF } from 'src/graphql'
import { graphqlResult } from 'src/utils'
import { _Account, Account } from '../account'
import { constants } from '../../constant'

export const useMemeStore = defineStore('meme', {
  state: () => ({}),
  actions: {
    balanceOf(
      req: BalanceOfRequest,
      memeApplication: Account,
      done?: (error: boolean, balance?: string) => void
    ) {
      const url = _Account.applicationUrl(
        constants.PROXY_SERVERNAME,
        'proxy',
        memeApplication
      )
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            BALANCE_OF,
            {
              owner: req.owner
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const balance = graphqlResult.data(res, 'balanceOf') as string
        done?.(false, balance)
      })

      onError(() => {
        done?.(true)
      })
    }
  },
  getters: {}
})
