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

export const LATEST_TRANSACTIONS = gql`
  query latestTransactions($startId: Int) {
    latestTransactions(startId: $startId)
  }
`

export const CALCULATE_AMOUNT_LIQUIDITY = gql`
  query calculateAmountLiquidity(
    $amount0Desired: Amount
    $amount1Desired: Amount
  ) {
    calculateAmountLiquidity(
      amount0Desired: $amount0Desired
      amount1Desired: $amount1Desired
    ) {
      liquidity
      amount0
      amount1
    }
  }
`

export const LIQUIDITY = gql`
  query liquidity($owner: String!) {
    liquidity(owner: $owner) {
      liquidity
      amount0
      amount1
    }
  }
`

export const ADD_LIQUIDITY = gql`
  mutation addLiquidity(
    $amount0In: Amount!
    $amount1In: Amount!
    $amount0OutMin: Amount
    $amount1OutMin: Amount
    $to: Account
    $blockTimestamp: Timestamp
  ) {
    addLiquidity(
      amount0In: $amount0In
      amount1In: $amount1In
      amount0OutMin: $amount0OutMin
      amount1OutMin: $amount1OutMin
      to: $to
      blockTimestamp: $blockTimestamp
    )
  }
`

export const REMOVE_LIQUIDITY = gql`
  mutation removeLiquidity(
    $liquidity: Amount!
    $amount0OutMin: Amount
    $amount1OutMin: Amount
    $to: Account
    $blockTimestamp: Timestamp
  ) {
    removeLiquidity(
      liquidity: $liquidity
      amount0OutMin: $amount0OutMin
      amount1OutMin: $amount1OutMin
      to: $to
      blockTimestamp: $blockTimestamp
    )
  }
`
