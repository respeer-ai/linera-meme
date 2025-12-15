import { NOTIFICATIONS } from 'src/graphql'
import { graphqlResult } from 'src/utils/index'
import { type NotificationsSubscription } from 'src/__generated__/graphql/service/graphql'
import { getClientOptions } from 'src/apollo'
import { ApolloClient } from '@apollo/client'
import { provideApolloClient, useSubscription } from '@vue/apollo-composable'

export class Subscription {
  unsubscribe: () => void = undefined as unknown as () => void

  constructor(
    httpUrl: string,
    wsUrl: string,
    chainId: string,
    onNewBlock: (height: number, hash: string) => void,
  ) {
    const options = /* await */ getClientOptions(httpUrl, wsUrl)
    const apolloClient = new ApolloClient(options)

    const { /* result, refetch, fetchMore, */ stop, onResult, onError } = provideApolloClient(
      apolloClient,
    )(() =>
      useSubscription(NOTIFICATIONS, {
        chainId,
      }),
    )

    onError((error) => {
      console.log(`Fail subscribe to ${chainId}: ${error}`)
    })

    onResult((res) => {
      const notifications = (graphqlResult.rootData(res) as NotificationsSubscription)
        .notifications as unknown
      const reason = graphqlResult.keyValue(notifications, 'reason')
      const newBlock = graphqlResult.keyValue(reason, 'NewBlock')
      if (newBlock) {
        onNewBlock?.(
          graphqlResult.keyValue(newBlock, 'height') as number,
          graphqlResult.keyValue(newBlock, 'hash') as string,
        )
      }
    })

    this.unsubscribe = stop
  }
}
