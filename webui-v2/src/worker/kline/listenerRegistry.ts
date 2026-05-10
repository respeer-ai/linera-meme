import { type KlineEventType } from './runner'
import { type ListenerFunc } from './kline'

export type KlineListenerRegistry = Map<KlineEventType, ListenerFunc>

export const registerKlineListener = (
  listeners: KlineListenerRegistry,
  type: KlineEventType,
  listener: ListenerFunc,
) => {
  listeners.set(type, listener)
}

export const unregisterKlineListener = (
  listeners: KlineListenerRegistry,
  type: KlineEventType,
  listener: ListenerFunc,
) => {
  if (listeners.get(type) !== listener) return
  listeners.delete(type)
}
