import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from '../apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { CREATOR_CHAIN_ID } from '../graphql'
import { graphqlResult } from '.'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const creatorChainId = async (
  endpoint: 'proxy' | 'swap'
): Promise<string> => {
  return new Promise((resolve, reject) => {
    const { /* result, refetch, fetchMore, */ onResult, onError } =
      provideApolloClient(apolloClient)(() =>
        useQuery(
          CREATOR_CHAIN_ID,
          {
            endpoint
          },
          {
            fetchPolicy: 'network-only'
          }
        )
      )

    onResult((res) => {
      resolve(graphqlResult.data(res, 'creatorChainId') as string)
    })

    onError((e) => {
      reject(e)
    })
  })
}
