import { defineStore } from 'pinia'
import { constants } from '../../constant'
import {
  type LiquidityAmount,
  type CalculateLiquidityAmountPairRequest,
  type LiquidityRequest,
} from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { CALCULATE_AMOUNT_LIQUIDITY, LIQUIDITY } from 'src/graphql'
import { graphqlResult } from 'src/utils'
import { _Account, type Account } from '../account'

export const usePoolStore = defineStore('pool', {
  state: () => ({}),
  actions: {
    calculateLiquidityAmountPair(
      req: CalculateLiquidityAmountPairRequest,
      poolApplication: Account,
      done?: (error: boolean, liquidity?: LiquidityAmount) => void,
    ) {
      const url = _Account.applicationUrl(constants.SWAP_URL, poolApplication)
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(
        apolloClient,
      )(() =>
        useQuery(
          CALCULATE_AMOUNT_LIQUIDITY,
          {
            amount0Desired: req.amount0Desired,
            amount1Desired: req.amount1Desired,
          },
          {
            fetchPolicy: 'network-only',
          },
        ),
      )

      onResult((res) => {
        const liquidity = graphqlResult.data(res, 'calculateAmountLiquidity') as LiquidityAmount
        done?.(false, liquidity)
      })

      onError(() => {
        done?.(true)
      })
    },
    liquidity(
      req: LiquidityRequest,
      poolApplication: Account,
      done?: (error: boolean, liquidity?: LiquidityAmount) => void,
    ) {
      const url = _Account.applicationUrl(constants.SWAP_URL, poolApplication)
      const options = /* await */ getClientOptions(url)
      const apolloClient = new ApolloClient(options)

      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(
        apolloClient,
      )(() =>
        useQuery(
          LIQUIDITY,
          {
            owner: req.owner,
          },
          {
            fetchPolicy: 'network-only',
          },
        ),
      )

      onResult((res) => {
        const liquidity = graphqlResult.data(res, 'liquidity') as LiquidityAmount
        done?.(false, liquidity)
      })

      onError(() => {
        done?.(true)
      })
    },
  },
  getters: {},
})
