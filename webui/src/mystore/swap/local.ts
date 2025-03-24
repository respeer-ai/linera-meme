import { defineStore } from 'pinia'
import { API, Token, GetTokensResponse, TokenPair, GetTokenPairsResponse, KPointTypeInfo, GetKPointTypesResponse } from './types'
import { doActionWithError } from '../action'
import { NotifyType } from '../notification'
import { useHostStore } from '../host'

export const useSwapStore = defineStore('useSwapStore', {
  state: () => ({
    SelectedToken: null as Token | null,
    SelectedTokenPair: null as TokenPair | null,
    Tokens: [] as Token[],
    TokenPairs: [] as TokenPair[],
    KPointTypes: [] as KPointTypeInfo[]
  }),
  actions: {
    getTokens (done?: (error: boolean, rows: Token[]) => void) {
      doActionWithError<unknown, GetTokensResponse>(
        useHostStore().formalizeKlinePath(API.GetTokens),
        {},
        {
          Error: {
            Title: 'Get tokens',
            Message: 'Failed get tokens',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetTokensResponse): void => {
          resp.Infos.sort()
          this.Tokens = resp.Infos
          done?.(false, resp.Infos)
        }, () => {
          done?.(true, [])
        }
      )
    },
    getTokenPairsByTokenZeroID (done?: (error: boolean, rows: TokenPair[]) => void) {
      if (!this.SelectedToken) {
        this.SelectedTokenPair = null
        return
      }
      doActionWithError<unknown, GetTokenPairsResponse>(
        useHostStore().formalizeKlinePath(API.GetTokenPairs),
        { Conds: { TokenZeroID: { Op: 'eq', Value: this.SelectedToken.ID } } },
        {
          Error: {
            Title: 'Get token pairs',
            Message: 'Failed get token pairs',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetTokenPairsResponse): void => {
          resp.Infos.sort()
          this.TokenPairs = resp.Infos
          done?.(false, resp.Infos)
        }, () => {
          done?.(true, [])
        }
      )
    },
    getKPointTypes (done?: (error: boolean, infos: KPointTypeInfo[]) => void) {
      doActionWithError<unknown, GetKPointTypesResponse>(
        useHostStore().formalizeKlinePath(API.GetKPointTypes),
        {},
        {
          Error: {
            Title: 'Get kpoint types',
            Message: 'Failed get kpoint types',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp) => {
          this.KPointTypes = resp.Infos
          done?.(false, resp.Infos)
        },
        () => { done?.(true, []) }
      )
    }
  }
})
