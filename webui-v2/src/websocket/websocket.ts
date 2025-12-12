export interface Notification {
  notification: string;
  value: unknown;
}

export class _WebSocket {
  private onMessageCb: (message: Notification) => void = undefined as unknown as (
    message: Notification,
  ) => void;

  private onErrorCb: (e: Event) => void = undefined as unknown as (e: Event) => void;

  constructor(url: string) {
    const socket = new WebSocket(url);

    socket.onopen = () => this.onOpen();
    socket.onmessage = (event) => this.onMessage(event);
    socket.onclose = () => this.onClose();
    socket.onerror = (event) => this.onError(event);
  }

  onOpen() {
    console.log('Websocket opened');
  }

  withOnMessage(cb: (message: Notification) => void) {
    this.onMessageCb = cb;
  }

  onMessage(message: MessageEvent) {
    // Here it must be parsed
    const notification = JSON.parse(message.data as string) as Notification;
    this.onMessageCb?.(notification);
  }

  onClose() {
    console.log('Websocket closed');
  }

  withOnError(cb: (e: Event) => void) {
    this.onErrorCb = cb;
  }

  onError(e: Event) {
    this.onErrorCb?.(e);
  }
}
