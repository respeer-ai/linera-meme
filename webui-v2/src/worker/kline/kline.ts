import {
  type FetchedPointsPayload,
  type FetchedTransactionsPayload,
  type FetchPointsPayload,
  type FetchTransactionsPayload,
  type KlineEvent,
  type KlineEventType,
  type LoadedPointsPayload,
  type LoadedTransactionsPayload,
  type LoadPointsPayload,
  type LoadTransactionsPayload,
  type NewPointsPayload,
  type NewTransactionsPayload,
  type SortedPointsPayload,
  type SortedTransactionsPayload,
  type SortPointsPayload,
  type SortTransactionsPayload,
} from './runner'
import { registerKlineListener, unregisterKlineListener } from './listenerRegistry'

type KlineResponseType =
  | FetchedPointsPayload
  | FetchedTransactionsPayload
  | LoadedPointsPayload
  | LoadedTransactionsPayload
  | SortedPointsPayload
  | SortedTransactionsPayload
export type ListenerFunc = (payload: KlineResponseType) => void

export class KlineWorker {
  private static _instance: KlineWorker | undefined = undefined

  private _worker: Worker | undefined = undefined

  private _listeners: Map<KlineEventType, ListenerFunc> = new Map<KlineEventType, ListenerFunc>()

  private constructor() {
    this._worker = new Worker(new URL('./worker.ts', import.meta.url), {
      type: 'module',
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
      | NewPointsPayload
      | NewTransactionsPayload
      | SortPointsPayload
      | SortTransactionsPayload,
  ) => {
    KlineWorker.getKlineWorker()._worker?.postMessage({
      type,
      payload,
    })
  }

  public static on = (type: KlineEventType, listener: ListenerFunc) => {
    registerKlineListener(KlineWorker.getKlineWorker()._listeners, type, listener)
  }

  public static off = (type: KlineEventType, listener: ListenerFunc) => {
    unregisterKlineListener(KlineWorker.getKlineWorker()._listeners, type, listener)
  }

  public static terminate = () => {
    KlineWorker.getKlineWorker()._worker?.terminate()
  }
}
