import {
  FetchedPointsPayload,
  FetchedTransactionsPayload,
  FetchPointsPayload,
  FetchTransactionsPayload,
  KlineEvent,
  KlineEventType,
  LoadedPointsPayload,
  LoadedTransactionsPayload,
  LoadPointsPayload,
  LoadTransactionsPayload
} from './runner'

type KlineResponseType =
  | FetchedPointsPayload
  | FetchedTransactionsPayload
  | LoadedPointsPayload
  | LoadedTransactionsPayload
export type ListenerFunc = (payload: KlineResponseType) => void

export class KlineWorker {
  // eslint-disable-next-line no-use-before-define
  private static _instance: KlineWorker | undefined = undefined

  private _worker: Worker | undefined = undefined

  // eslint-disable-next-line func-call-spacing
  private _listeners: Map<KlineEventType, ListenerFunc> = new Map<
    KlineEventType,
    ListenerFunc
  >()

  private constructor() {
    this._worker = new Worker(new URL('./worker.ts', import.meta.url), {
      type: 'module'
    })

    this._worker.onmessage = (message: MessageEvent) => {
      const event = message.data as KlineEvent
      this._listeners.get(event.type)?.(event.payload as KlineResponseType)
    }
  }

  public static getKlineWorker = () => {
    if (KlineWorker._instance) return KlineWorker._instance
    KlineWorker._instance = new KlineWorker()
    return KlineWorker._instance
  }

  public static send = (
    type: KlineEventType,
    payload?:
      | FetchPointsPayload
      | FetchTransactionsPayload
      | LoadPointsPayload
      | LoadTransactionsPayload
  ) => {
    KlineWorker.getKlineWorker()._worker?.postMessage({
      type,
      payload
    })
  }

  public static on = (type: KlineEventType, listener: ListenerFunc) => {
    KlineWorker.getKlineWorker()._listeners.set(type, listener)
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  public static off = (type: KlineEventType, listener: ListenerFunc) => {
    KlineWorker.getKlineWorker()._listeners.delete(type)
  }

  public static terminate = () => {
    KlineWorker.getKlineWorker()._worker?.terminate()
  }
}
