import { defineStore } from 'pinia'
import { doActionWithError } from '../action'
import { NotifyType } from '../notification'
import { CalSwapAmountResponse, GetBalanceResponse, GetLiquidityResponse } from './types'
import { gql } from '@apollo/client'
import { useHostStore } from '../host'

export const useWalletStore = defineStore('useWalletStore', {
  state: () => ({}),
  actions: {
    getBalance (erc20AppAddr: string, accountChainID: string, accountAddr: string, done?: (error: boolean, balance: string) => void) {
      const url = useHostStore().swapApplicationTokenPath(erc20AppAddr)
      const req = { query: `query{\n  balanceOf(owner:{\n    chain_id: "${accountChainID}"\n    owner: "User:${accountAddr}"\n  })\n}` }
      doActionWithError<unknown, GetBalanceResponse>(
        url,
        req,
        {
          Error: {
            Title: 'Get balance',
            Message: 'Failed get balance',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetBalanceResponse): void => {
          done?.(false, resp.data.balanceOf)
        },
        () => {
          done?.(true, '0')
        }
      )
    },
    calSwapAmount (tokenZeroAppAddr: string, tokenOneAppAddr: string, outAmount: number, done?: (error: boolean, amount: number) => void) {
      const url = useHostStore().swapApplicationPath()
      const req = { query: `query{\n  calculateSwapAmount(token0:"${tokenZeroAppAddr}",token1:"${tokenOneAppAddr}",amount1:"${outAmount}")\n}` }
      doActionWithError<unknown, CalSwapAmountResponse>(
        url,
        req,
        {
          Error: {
            Title: 'Calculate swap amount',
            Message: 'Failed calculate swap amount',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: CalSwapAmountResponse): void => {
          done?.(false, resp.data.calculateSwapAmount)
        },
        () => { done?.(true, 0) }
      )
    },
    swapAmount (token0: string, token1: string, publicKey: string, outAmount: number) {
      const mutate = gql`
        mutation swap ($token0: String!, $token1: String!, $amount0In: String!, $amount1In: String!, $amount0OutMin: String!, $amount1OutMin: String!) {
          swap (
            token0: $token0,
            token1: $token1,
            amount0In: $amount0In,
            amount1In: $amount1In,
            amount0OutMin: $amount0OutMin,
            amount1OutMin: $amount1OutMin
          )
        }
      `
      return new Promise((resolve, reject) => {
        window.linera.request({
          method: 'linera_graphqlMutation',
          params: {
            publicKey: publicKey,
            applicationId: useHostStore().swapApplicationId,
            query: {
              query: mutate.loc?.source?.body,
              variables: {
                token0: token0,
                token1: token1,
                amount0In: outAmount.toString(),
                amount1In: '0',
                amount0OutMin: '0',
                amount1OutMin: '0'
              }
            }
          }
        }).then((result) => {
          resolve(result)
        }).catch((e) => {
          reject(e)
        })
      })
    },
    addLiquidity (token0: string, token1: string, publicKey: string, token0Amount: number, token1Amount: number) {
      const mutate = gql`
        mutation addLiquidity ($token0: String!, $token1: String!, $amount0Desired: String!, $amount1Desired: String!, $amount0Min: String!, $amount1Min: String!, $deadline: Timestamp!) {
          addLiquidity(token0: $token0, token1: $token1, amount0Desired: $amount0Desired, amount1Desired: $amount1Desired, amount0Min: $amount0Min, amount1Min: $amount1Min, deadline: $deadline)
        }
      `
      return new Promise((resolve, reject) => {
        window.linera.request({
          method: 'linera_graphqlMutation',
          params: {
            publicKey: publicKey,
            applicationId: useHostStore().swapApplicationId,
            query: {
              query: mutate.loc?.source?.body,
              variables: {
                token0: token0,
                token1: token1,
                amount0Desired: token0Amount.toString(),
                amount1Desired: token1Amount.toString(),
                amount0Min: '0',
                amount1Min: '0',
                deadline: 0
              }
            }
          }
        }).then((result) => {
          resolve(result)
        }).catch((e) => {
          reject(e)
        })
      })
    },
    removeLiquidity (token0: string, token1: string, publicKey: string, liquidity: number, token0MinAmount: number, token1MinAmount: number) {
      const mutate = gql`
        mutation removeLiquidity ($token0: String!, $token1: String!, $liquidity: String!, $amount0Min: String!, $amount1Min: String!, $deadline: String!) {
        removeLiquidity(token0: $token0, token1: $token1, liquidity: $liquidity, amount0Min: $amount0Min, amount1Min: $amount1Min, deadline: $deadline)
      }
      `
      return new Promise((resolve, reject) => {
        window.linera.request({
          method: 'linera_graphqlMutation',
          params: {
            publicKey: publicKey,
            applicationId: useHostStore().swapApplicationId,
            query: {
              query: mutate.loc?.source?.body,
              variables: {
                token0: token0,
                token1: token1,
                liquidity: liquidity.toString(),
                amount0Min: token0MinAmount.toString(),
                amount1Min: token1MinAmount.toString(),
                deadline: 0
              }
            }
          }
        }).then((result) => {
          resolve(result)
        }).catch((e) => {
          reject(e)
        })
      })
    },
    getOwnerLiquidity (poolID: number, accountChainID: string, accountAddr: string, done?: (error: boolean, liquidity: string) => void) {
      const url = useHostStore().swapApplicationPath()
      const req = { query: `query{\n  getOwnerLiquidity(poolId:${poolID},\n owner:{\n    chain_id: "${accountChainID}"\n    owner: "User:${accountAddr}"\n  })\n}` }
      doActionWithError<unknown, GetLiquidityResponse>(
        url,
        req,
        {
          Error: {
            Title: 'Get liquidity',
            Message: 'Failed get liquidity',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetLiquidityResponse): void => {
          done?.(false, resp.data.getOwnerLiquidity)
        },
        () => {
          done?.(true, '0')
        }
      )
    }
  }
})
