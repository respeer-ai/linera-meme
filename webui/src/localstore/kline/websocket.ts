import { Points, Notification } from './types'

export class _WebSocket {
  private onMessageCb: (message: Map<string, Points[]>) => void = undefined as unknown as (message: Map<string, Points[]>) => void
  private onErrorCb: (e: Event) => void = undefined as unknown as (e: Event) => void

  constructor(url: string) {
    const socket = new WebSocket(url)

    socket.onopen = this.onOpen
    socket.onmessage = (event) => this.onMessage(event)
    socket.onclose, this.onClose
    socket.onerror = (event) => this.onError(event)
  }

  onOpen () {
    console.log('Kline websocket opened')
  }

  withOnMessage (cb: (message: Map<string, Points[]>) => void) {
    this.onMessageCb = cb
  }

  onMessage (message: MessageEvent) {
    const notification = JSON.parse(message.data) as Notification
    if (notification.notification !== 'kline') return
    this.onMessageCb?.(new Map(Object.entries(notification.value)))
  }

  onClose () {
    console.log('Kline websocket closed')
  }

  withOnError (cb: (e: Event) => void) {
    this.onErrorCb = cb
  }

  onError (e: Event) {
    this.onErrorCb?.(e)
  }
}
