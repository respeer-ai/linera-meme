import { gql } from '@apollo/client/core'

export const CREATE_POOL = gql`
  mutation createPool(
    $token0: ApplicationId!
    $token1: ApplicationId
    $amount0: Amount!
    $amount1: Amount!
    $to: Account
  ) {
    createPool(
      token0: $token0
      token1: $token1
      amount0: $amount0
      amount1: $amount1
      to: $to
    )
  }
`
