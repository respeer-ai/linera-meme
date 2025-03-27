import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { CREATOR_CHAIN_ID } from 'src/graphql'
import { graphqlResult } from 'src/utils'

const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/56381194be19cddc8bfe09b3d3e63b7462026f0bb238b21ef91b65023d3c53bc/applications/6605301e41caa7ef70c8136168c9011a91dd1d6195a3dd3b8b16485e39e4133b',
  'http://api.ams.respeer.ai/api/ams/chains/45e21c3d39a4d35bd905a02b8a4f9753c63cb5a02dce306af691794d72dbbb16/applications/6ff725592a0639794a41ef2800eec6e5dd4c0fad00032cf48988fce43f62e364',
  'http://api.linerameme.fun/api/proxy/chains/64116b2bcfddb4bf79ec4f265bbc2a7bc3a0e8b3b347421986736faa5fa5d9fd/applications/593604ef27bb4f0a801056dc6a5cc73c4c7918c70714633328224454d910f617',
  'http://api.lineraswap.fun/api/swap/chains/4c8dcd102356fbd1ec69f4c2d245b3a1ab155adf9744285bbfcf6bd9ecce65a4/applications/c329097a0c479673fffa63f7cf5ce6a9a1d32a30973d4f2392c4e8596383bc92'
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
