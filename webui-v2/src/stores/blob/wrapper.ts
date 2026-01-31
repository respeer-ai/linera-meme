import { type BlobData } from 'src/__generated__/graphql/blob/graphql'
import { NotifyType } from '../notify'
import { useBlobStore } from './store'

const blob = useBlobStore()

export class Blob {
  static existBlob = (blobHash: string) => blob.existBlob(blobHash)

  static blobs = () => blob.blobs

  static getBlobsList = (done?: (error: boolean, rows?: BlobData[]) => void) => {
    blob.listBlobs(
      {
        limit: 800,
        Message: {
          Error: {
            Title: 'Get blobs list',
            Message: 'Failed get blobs list',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      done,
    )
  }

  static blobPath = (blobData: BlobData) => blob.blobPath(blobData)

  static blockHash = () => blob.blockHash

  static initialize = () => blob.initializeBlobGateway()
}
