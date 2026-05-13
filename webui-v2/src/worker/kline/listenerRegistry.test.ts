import { describe, expect, test } from 'bun:test'

import { KlineEventType } from './runner'
import { registerKlineListener, unregisterKlineListener } from './listenerRegistry'
import { type ListenerFunc } from './kline'

describe('kline worker listener registry', () => {
  test('does not let an old component unregister a newer listener for the same event type', () => {
    const listeners = new Map<KlineEventType, ListenerFunc>()
    const oldListener: ListenerFunc = () => undefined
    const newListener: ListenerFunc = () => undefined

    registerKlineListener(listeners, KlineEventType.FETCHED_POINTS, oldListener)
    registerKlineListener(listeners, KlineEventType.FETCHED_POINTS, newListener)
    unregisterKlineListener(listeners, KlineEventType.FETCHED_POINTS, oldListener)

    expect(listeners.get(KlineEventType.FETCHED_POINTS)).toBe(newListener)
  })

  test('unregisters the current listener when the owner unmounts', () => {
    const listeners = new Map<KlineEventType, ListenerFunc>()
    const listener: ListenerFunc = () => undefined

    registerKlineListener(listeners, KlineEventType.FETCHED_POINTS, listener)
    unregisterKlineListener(listeners, KlineEventType.FETCHED_POINTS, listener)

    expect(listeners.has(KlineEventType.FETCHED_POINTS)).toBe(false)
  })
})
