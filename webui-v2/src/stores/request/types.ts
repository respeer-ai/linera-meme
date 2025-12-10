import { Notification } from '../notify'

export interface ReqMessage {
  Info?: Notification
  Error?: Notification
}

export interface BaseRequest {
  Message?: ReqMessage
}

export interface NotifyRequest {
  NotifyMessage?: ReqMessage
}
