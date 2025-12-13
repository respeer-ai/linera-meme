import { type BaseRequest } from '../request'

export interface ListBlobsRequest extends BaseRequest {
  createdAfter?: number
  limit: number
}
