import { NotifyType } from './const'

export interface Notification {
  Title?: string
  Message?: string
  Description?: string
  Popup?: boolean
  Type?: NotifyType
}

export interface ReqMessage {
  Info?: Notification
  Error?: Notification
}

export interface BaseRequest {
  Message: ReqMessage
}

export interface MyRequest {
  NotifyMessage: ReqMessage
}
