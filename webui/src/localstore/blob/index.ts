import { StoreType } from '../store'
import { constants } from 'src/constant'
import { PrepareBlobRequest } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useMutation } from '@vue/apollo-composable'
import { PREPARE_BLOB } from 'src/graphql'
import { graphqlResult } from 'src/utils'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export class BlobGateway {
  static imagePath(storeType: StoreType, imageHash: string): string {
    switch (storeType) {
      case StoreType.Blob:
      case StoreType.S3:
        return constants.APPLICATION_URLS.BLOB_GATEWAY + '/images/' + imageHash
      case StoreType.Ipfs:
        return imageHash
    }
  }

  static async prepareBlob(req: PrepareBlobRequest) {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
    const { mutate } = provideApolloClient(apolloClient)(() =>
      useMutation(PREPARE_BLOB)
    )
    const resp = await mutate({
      chainId: req.chainId,
      bytes: req.bytes
    })
    return graphqlResult.data(resp, 'prepareBlob')
  }
}
