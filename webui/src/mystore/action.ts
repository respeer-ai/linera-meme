import axios, { AxiosError, AxiosResponse } from 'axios'
import * as notification from './notification'

const _notification = notification.useNotificationStore()

function processError (err: AxiosError, message?: notification.Notification) {
  if (message) {
    message.Description = err.response?.statusText
  }
  if (message) {
    _notification.Notifications.push(message)
  }
}

function doAction<MyRequest, MyResponse> (
  url: string,
  req: MyRequest,
  message: notification.ReqMessage,
  success: (resp: MyResponse) => void) {
  const _url = new URL(url)
  const pathname = _url.pathname
  const api = axios.create({
    baseURL: _url.protocol + '//' + _url.host,
    headers: {
      'Content-Type': 'application/json'
    },
    withCredentials: false,
    responseType: 'json',
    timeout: 60000
  })
  api
    .post<MyRequest, AxiosResponse<MyResponse>>(pathname, req)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message.Info) {
        _notification.Notifications.push(message.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message.Error)
    })
}
function doActionWithError<MyRequest, MyResponse> (
  url: string,
  req: MyRequest,
  message: notification.ReqMessage,
  success: (resp: MyResponse) => void,
  error: () => void) {
  const _url = new URL(url)
  const pathname = _url.pathname
  const headers: Record<string, string | number | boolean> = {
    'Content-Type': 'application/json'
  }
  const api = axios.create({
    baseURL: _url.protocol + '//' + _url.host,
    headers,
    withCredentials: false,
    responseType: 'json',
    timeout: 60000
  })
  api
    .post<MyRequest, AxiosResponse<MyResponse>>(pathname, req)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message.Info) {
        _notification.Notifications.push(message.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message.Error)
      error()
    })
}

function doGet<MyRequest, MyResponse> (
  url: string,
  req: MyRequest,
  message: notification.ReqMessage,
  success: (resp: MyResponse) => void) {
  axios
    .get<MyRequest, AxiosResponse<MyResponse>>(url)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message.Info) {
        _notification.Notifications.push(message.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message.Error)
    })
}

function doGetWithError<MyRequest, MyResponse> (
  url: string,
  req: MyRequest,
  message: notification.ReqMessage,
  success: (resp: MyResponse) => void,
  error: () => void) {
  axios
    .get<MyRequest, AxiosResponse<MyResponse>>(url)
    .then((response: AxiosResponse<MyResponse>) => {
      success(response.data)
      if (message.Info) {
        _notification.Notifications.push(message.Info)
      }
    })
    .catch((err: AxiosError) => {
      processError(err, message.Error)
      error()
    })
}

export {
  doAction,
  doActionWithError,
  doGet,
  doGetWithError
}
