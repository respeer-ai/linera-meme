import { StoreType } from '../store'
import { constants } from 'src/constant'
import { defineStore } from 'pinia'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { LIST } from 'src/graphql'
import { graphqlResult } from 'src/utils'
import { type BlobData } from 'src/__generated__/graphql/blob/graphql'
import { type ListBlobsRequest } from './types'

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
}

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useBlobStore = defineStore('blob', {
  state: () => ({
    blobs: [] as Array<BlobData>
  }),
  actions: {
    listBlobs(
      req: ListBlobsRequest,
      done?: (error: boolean, rows?: BlobData[]) => void
    ) {
      const { /* result, refetch, fetchMore, */ onResult, onError } =
        provideApolloClient(apolloClient)(() =>
          useQuery(
            LIST,
            {
              createdAfter: req.createdAfter,
              limit: req.limit,
              endpoint: 'blob'
            },
            {
              fetchPolicy: 'network-only'
            }
          )
        )

      onResult((res) => {
        const applications = graphqlResult.data(res, 'list') as BlobData[]
        this.appendApplications(applications)
        done?.(false, applications)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendApplications(blobs: BlobData[]) {
      blobs.forEach((blob) => {
        const index = this.blobs.findIndex(
          (el) => el.blobHash === blob.blobHash
        )
        this.blobs.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, blob)
      })
    }
  },
  getters: {
    blobPath(): (blob: BlobData) => string {
      return (blob: BlobData) => {
        console.log(
          BlobGateway.imagePath(
            blob.storeType as StoreType,
            blob.blobHash as string
          )
        )
        return BlobGateway.imagePath(
          blob.storeType as StoreType,
          blob.blobHash as string
        )
      }
    },
    existBlob(): (blobHash: string) => boolean {
      return (blobHash: string) => {
        return this.blobs.findIndex((el) => el.blobHash === blobHash) >= 0
      }
    }
  }
})

export * from './types'
