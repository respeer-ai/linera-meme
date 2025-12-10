import { gql } from '@apollo/client/core'

export const CREATE_POOL = gql`
  mutation createPool(
    $token0CreatorChainId: ChainId!
    $token0: ApplicationId!
    $token1CreatorChainId: ChainId
    $token1: ApplicationId
    $amount0: Amount!
    $amount1: Amount!
    $to: Account
  ) {
    createPool(
      token0CreatorChainId: $token0CreatorChainId
      token0: $token0
      token1CreatorChainId: $token1CreatorChainId
      token1: $token1
      amount0: $amount0
      amount1: $amount1
      to: $to
    )
  }
`
