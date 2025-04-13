import { FetchPointsPayload, FetchTransactionsPayload, KlineEvent, KlineEventType, KlineRunner } from './runner'

self.onmessage = async (message: MessageEvent) => {
  const event = message.data as KlineEvent
  switch (event.type) {
    case KlineEventType.FETCH_POINTS:
      return await KlineRunner.handleFetchPoints(event.payload as FetchPointsPayload)
    case KlineEventType.FETCH_TRANSACTIONS:
      return await KlineRunner.handleFetchTransactions(
        event.payload as FetchTransactionsPayload
      )
  }
}
