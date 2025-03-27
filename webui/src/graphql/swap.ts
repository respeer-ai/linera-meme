import { gql } from '@apollo/client/core'

export const POOLS = gql`
  query pools {
    pools {
      poolId
      token0
      token1
    }
  }
`

export const LATEST_TRANSACTIONS = gql`
  query latestTransactions {
    latestTransactions {
      token0
      token1
      transaction
    }
  }
`
