import { BaseRequest } from '../request'

export interface PrepareBlobRequest extends BaseRequest {
  chainId: string
  bytes: number[]
}
