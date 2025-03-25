import { StoreType } from '../store'
import { constants } from 'src/constant'
import { PrepareBlobRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { PREPARE_BLOB } from 'src/graphql'
import { graphqlResult } from 'src/utils'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export class BlobGateway {
  static imagePath (storeType: StoreType, imageHash: string): string {
    switch (storeType) {
      case StoreType.Blob:
      case StoreType.S3:
        return constants.APPLICATION_URLS.BLOB_GATEWAY + '/images/' + imageHash
      case StoreType.Ipfs:
        return imageHash
    }
  }

  static prepareBlob(req: PrepareBlobRequest, done?: (error: boolean, blobHash?: string) => void) {
    const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(apolloClient)(() => useQuery(PREPARE_BLOB, {
      endpoint: 'rpc'
    }, {
      fetchPolicy: 'network-only'
    }))

    onResult((res) => {
      done?.(false, graphqlResult.data(res, 'prepareBlob') as string)
    })

    onError(() => {
      done?.(true)
    })
  }
}
