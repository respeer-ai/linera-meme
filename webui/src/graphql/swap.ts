import { gql } from '@apollo/client/core'

export const POOLS = gql`
  query pools {
    pools {
      poolId
      token0
      token1
      poolApplication
      latestTransaction
      token0Price
      token1Price
    }
  }
`
