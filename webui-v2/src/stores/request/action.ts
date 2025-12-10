import { type AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import { useNotificationStore, type Notification } from '../notify'
import { type ReqMessage } from './types'
import { createAPI } from './axiosapi'

function processError(err: AxiosError, message?: Notification) {
  if (message) {
    message.Description = err.response?.statusText as string
  }
  const notification = useNotificationStore()
  if (message) {
    notification.pushNotification(message)
  }
}

function doAction<MyRequest, MyResponse>(
  url: string,
  req: MyRequest,
  message: ReqMessage | undefined,
  success: (resp: MyResponse) => void
) {
  const api = createAPI(url) as AxiosInstance
  api
    .post<MyRequest, AxiosResponse<MyResponse>>(url, req)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message?.Info) {
        const notification = useNotificationStore()
        notification.pushNotification(message?.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message?.Error)
    })
}
function doActionWithError<MyRequest, MyResponse>(
  url: string,
  req: MyRequest,
  message: ReqMessage | undefined,
  success: (resp: MyResponse) => void,
  error: () => void
) {
  const api = createAPI(url) as AxiosInstance
  api
    .post<MyRequest, AxiosResponse<MyResponse>>(url, req)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message?.Info) {
        const notification = useNotificationStore()
        notification.pushNotification(message.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message?.Error)
      error()
    })
}

function doGet<MyRequest, MyResponse>(
  url: string,
  req: MyRequest,
  message: ReqMessage | undefined,
  success: (resp: MyResponse) => void
) {
  const api = createAPI(url) as AxiosInstance
  api
    .get<MyRequest, AxiosResponse<MyResponse>>(url)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message?.Info) {
        const notification = useNotificationStore()
        notification.pushNotification(message?.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message?.Error)
    })
}

function doGetWithError<MyRequest, MyResponse>(
  url: string,
  req: MyRequest,
  message: ReqMessage | undefined,
  success: (resp: MyResponse) => void,
  error: () => void
) {
  const api = createAPI(url) as AxiosInstance
  api
    .get<MyRequest, AxiosResponse<MyResponse>>(url)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message?.Info) {
        const notification = useNotificationStore()
        notification.pushNotification(message?.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message?.Error)
      error()
    })
}

export { doAction, doActionWithError, doGet, doGetWithError }
