import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { CREATOR_CHAIN_ID } from 'src/graphql'
import { graphqlResult } from 'src/utils'

const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/c40d1d10e734a2a85ec41bb5feae21c2eda9c6871a75fe026fa0d2c1129c5a50/applications/592c1f8862bc423ec95bf4af01ab82d8982cc831c955c8b147f894aae730a407',
  'http://api.ams.respeer.ai/api/ams/chains/39b461a61e95ba507527ac2e655ad0558b8e65071ac3de628667a8e340f7249e/applications/01bbf912dadd4f88108187f9537f9e9c6ddf11f9cc76cf2b59e98080c110355a',
  'http://api.linerameme.fun/api/proxy/chains/161183880e235f18aed43c62be3c5d7ff66abf7a5db48b71192ae2e8699b1d30/applications/c9987dbf572d4805a2623ba9225f8ad2435d12192d3313df104bab993c18da8a',
  'http://api.lineraswap.fun/api/swap/chains/57b850c48b93568ba6b17943267226d4e0a79adc5420ae12930f6b4b80317c24/applications/2af0b7eae2123e4b94efedd282e1b923bb4188cc2ccb5f164c802b3b54a6a966'
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
