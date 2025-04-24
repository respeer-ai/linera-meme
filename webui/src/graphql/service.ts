import { gql } from '@apollo/client/core'

export const BALANCES = gql`
  query balances($chainOwners: [ChainOwners!]!) {
    balances(chainOwners: $chainOwners)
  }
`

export const NOTIFICATIONS = gql`
  subscription notifications($chainId: ChainId!) {
    notifications(chainId: $chainId)
  }
`
