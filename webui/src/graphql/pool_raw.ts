import { gql } from '@apollo/client/core'

export const SWAP = gql`
  mutation swap(
    $amount0In: Amount
    $amount1In: Amount
    $amount0OutMin: Amount
    $amount1OutMin: Amount
    $to: Account
    $blockTimestamp: Timestamp
  ) {
    swap(
      amount0In: $amount0In
      amount1In: $amount1In
      amount0OutMin: $amount0OutMin
      amount1OutMin: $amount1OutMin
      to: $to
      blockTimestamp: $blockTimestamp
    )
  }
`
