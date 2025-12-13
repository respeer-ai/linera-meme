import { useBlobStore } from './store'

const blob = useBlobStore()

export class Blob {
  static existBlob = (blobHash: string) => blob.existBlob(blobHash)
}
