export interface Notification {
  notification: string
  value: unknown
}

export class _WebSocket {
  private onMessageCb: (message: Notification) => void = undefined as unknown as (
    message: Notification,
  ) => void

  private onErrorCb: (e: Event) => void = undefined as unknown as (e: Event) => void

  private socket?: WebSocket
  private reconnectTimer: number | undefined
  private readonly url: string

  constructor(url: string) {
    this.url = url
    this.connect()
  }

  private connect() {
    const socket = new WebSocket(this.url)

    socket.onopen = () => this.onOpen()
    socket.onmessage = (event) => this.onMessage(event)
    socket.onclose = () => this.onClose()
    socket.onerror = (event) => this.onError(event)

    this.socket = socket
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = undefined
      this.connect()
    }, 3000)
  }

  onOpen() {
    console.log('Websocket opened')
  }

  withOnMessage(cb: (message: Notification) => void) {
    this.onMessageCb = cb
  }

  onMessage(message: MessageEvent) {
    // Here it must be parsed
    const notification = JSON.parse(message.data as string) as Notification
    this.onMessageCb?.(notification)
  }

  onClose() {
    console.log('Websocket closed')

    this.scheduleReconnect()
  }

  withOnError(cb: (e: Event) => void) {
    this.onErrorCb = cb
  }

  onError(e: Event) {
    console.log('Websocket error: ', e)
    this.onErrorCb?.(e)
    this.scheduleReconnect()
  }
}
