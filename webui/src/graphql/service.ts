import { gql } from '@apollo/client/core'

export const BALANCES = gql`
  query balances($chainOwners: JSONObject!) {
    balances(chainOwners: $chainOwners)
  }
`

export const PREPARE_BLOB = gql`
  mutation prepareBlob($chainId: ChainId!, $bytes: [Int!]!) {
    prepareBlob(chainId: $chainId, bytes: $bytes)
  }
`
