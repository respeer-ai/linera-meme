import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { CREATOR_CHAIN_ID } from 'src/graphql'
import { graphqlResult } from 'src/utils'

const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/54152886b4fc4e44bc3dd17c0e6b2b38aa57ea786e69598f1043fc5416c00b7f/applications/dbbf9305fb0025d306b75056a70137f96a9e77b3774507d713f2c3fbcdb9e693',
  'http://api.ams.respeer.ai/api/ams/chains/85ae40f0c028600108db00521a4be4b4def15da98317b5f32cbd5367520bfcae/applications/f16689dc9d037b835c18bde8515e82d4c34b4ae989c84a4d259f3b19cc5f4bab',
  'http://api.linerameme.fun/api/proxy/chains/b012a4ff2b0cc83edd01797b94eeedfc5308da29255f2c0c56fa893d0f2de57a/applications/06dde12ccb705473d48ad43b0d08e49d9126309949e8fc6dc8c883e227eefd54',
  'http://api.lineraswap.fun/api/swap/chains/46afaeae5c8ba8baf5dcae6724ce4f92d3de28537bda44dda289cda34dd9abb8/applications/ce374b55ed6e2d526099bef1ba4a63d708b1c939852783e246b0c689917b36ca'
]

export const APPLICATION_URLS = {
  BLOB_GATEWAY: URLS[0],
  AMS: URLS[1],
  PROXY: URLS[2],
  SWAP: URLS[3]
}

export const RPC_URL = 'http://api.rpc.respeer.ai/api/rpc'
export const RPC_WS_URL = 'ws://api.rpc.respeer.ai/ws'

export const formalizeSchema = (url: string) => {
  return url.replace(
    'http://',
    process.env.NODE_ENV === 'production' ? 'https://' : 'http://'
  )
}

export const applicationId = (url: string) => {
  return url.split('/').at(-1)
}

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
