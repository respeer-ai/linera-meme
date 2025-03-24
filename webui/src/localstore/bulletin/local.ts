import { defineStore } from 'pinia'
import { API, TokenVolumn, GetOneDayVolumnResponse } from './types'
import { doActionWithError } from '../action'
import { NotifyType } from '../notification'
import { useHostStore } from '../host'

export const useBulletinStore = defineStore('useBulletinStore', {
  state: () => ({
    TokenVolumns: [] as TokenVolumn[]
  }),
  actions: {
    getOneDayVolumn (done?: (error: boolean, rows: TokenVolumn[]) => void) {
      doActionWithError<unknown, GetOneDayVolumnResponse>(
        useHostStore().formalizeKlinePath(API.GetOneDayVolumn),
        {},
        {
          Error: {
            Title: 'Get volume',
            Message: 'Failed get one day volume',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetOneDayVolumnResponse): void => {
          this.TokenVolumns = resp.Infos
          done?.(false, resp.Infos)
        }, () => {
          done?.(true, [])
        }
      )
    }
  }
})
