import { BaseRequest } from '../request'

export enum StoreType {
  Blob = 'Blob',
  Ipfs = 'Ipfs',
  S3 = 'S3'
}

export interface Application {
  // TODO: use Account after fix https://github.com/linera-io/linera-protocol/issues/3462
  creator: string
  applicationName: string
  applicationId: string
  // Preset application types could be added by operator
  applicationType: string
  keyWords: Array<string>
  logoStoreType: StoreType
  logo: string
  description: string
  twitter?: string
  telegram?: string
  discord?: string
  website?: string
  github?: string
  /// JSON spec of registered application
  spec: string
  createdAt: number
}

export interface GetApplicationsRequest extends BaseRequest {
  createdBefore?: number
  createdAfter?: number
  applicationType?: string
  spec?: string
  applicationIds?: Array<string>
  limit: number
}
