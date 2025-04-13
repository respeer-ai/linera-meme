import {
  FetchPointsPayload,
  FetchTransactionsPayload,
  KlineEvent,
  KlineEventType,
  KlineRunner,
  LoadPointsPayload,
  LoadTransactionsPayload,
  NewPointsPayload,
  NewTransactionsPayload
} from './runner'

self.onmessage = async (message: MessageEvent) => {
  const event = message.data as KlineEvent
  switch (event.type) {
    case KlineEventType.FETCH_POINTS:
      return await KlineRunner.handleFetchPoints(
        event.payload as FetchPointsPayload
      )
    case KlineEventType.FETCH_TRANSACTIONS:
      return await KlineRunner.handleFetchTransactions(
        event.payload as FetchTransactionsPayload
      )
    case KlineEventType.LOAD_POINTS:
      return await KlineRunner.handleLoadPoints(
        event.payload as LoadPointsPayload
      )
    case KlineEventType.LOAD_TRANSACTIONS:
      return await KlineRunner.handleLoadTransactions(
        event.payload as LoadTransactionsPayload
      )
    case KlineEventType.NEW_POINTS:
      return KlineRunner.handleNewPoints(event.payload as NewPointsPayload)
    case KlineEventType.NEW_TRANSACTIONS:
      return KlineRunner.handleNewTransactions(
        event.payload as NewTransactionsPayload
      )
  }
}
