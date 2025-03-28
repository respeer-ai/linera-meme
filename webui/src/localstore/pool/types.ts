import { BaseRequest } from '../request'

export interface LatestTransactionsRequest extends BaseRequest {
  startId?: number
}
