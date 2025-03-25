import { StoreType } from '../store'
import { constants } from 'src/constant'

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
}
