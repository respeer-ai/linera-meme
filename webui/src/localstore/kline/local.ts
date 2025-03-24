import { defineStore } from 'pinia'
import { API, KPoint, GetKPointsForLineResponse, EchartKPoints } from './types'
import { doActionWithError } from '../action'
import { NotifyType } from '../notification'
import { useHostStore } from '../host'

export const useKLineStore = defineStore('useKLineStore', {
  state: () => ({
    NeedInitKLine: true,
    SelectedKPType: undefined as string | undefined,
    SelectedTokenPairID: -1,
    OriginalTime: 0,
    EchartPoinsData: {
      CategoryItems: [],
      Nums: []
    } as EchartKPoints,
    RefreshKlineHistoryLock: false,
    EchartPoinsDataUpdate: 0,
    MaxKPoints: 1000,
    ResetKLineViewLock: 0
  }),
  actions: {
    refreshNewKPoints (done?: (error: boolean, rows: KPoint[]) => void) {
      if (this.SelectedKPType === null || this.SelectedTokenPairID === null || this.SelectedTokenPairID < 0) {
        return
      }
      doActionWithError<unknown, GetKPointsForLineResponse>(
        useHostStore().formalizeKlinePath(API.GetKPointsForLine),
        {
          KPointType: this.SelectedKPType,
          Limit: 20,
          Offset: 0,
          OriginalTime: this.OriginalTime,
          TokenPairID: this.SelectedTokenPairID
        },
        {
          Error: {
            Title: 'Get Kpoints',
            Message: 'Failed to get kpoints',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetKPointsForLineResponse): void => {
          if (this.OriginalTime === 0) {
            this.OriginalTime = resp.OriginalTime
          }
          if (resp.KPoints.length > 0) {
            this.OriginalTime = resp.KPoints[resp.KPoints.length - 1].Times[1] + 1
            this._refreshEchartKPoints(resp.KPoints, false)
          }
          if (this.EchartPoinsData.CategoryItems.length > this.MaxKPoints) {
            this.EchartPoinsData.CategoryItems.splice(0, this.EchartPoinsData.CategoryItems.length - this.MaxKPoints)
            this.EchartPoinsData.Nums.splice(0, this.EchartPoinsData.Nums.length - this.MaxKPoints)
          }

          done?.(false, resp.KPoints)
        }, () => {
          done?.(true, [])
        }
      )
    },
    refreshHistoryKPoints (done?: (error: boolean, rows: KPoint[]) => void) {
      if (this.SelectedKPType === null || this.SelectedTokenPairID === null || this.SelectedTokenPairID < 0) {
        return
      }
      if (this.EchartPoinsData.CategoryItems.length >= this.MaxKPoints) {
        return
      }
      if (this.RefreshKlineHistoryLock) {
        return
      }
      this.RefreshKlineHistoryLock = true
      doActionWithError<unknown, GetKPointsForLineResponse>(
        useHostStore().formalizeKlinePath(API.GetKPointsForLine),
        {
          KPointType: this.SelectedKPType,
          Limit: -100,
          Offset: -this.EchartPoinsData.CategoryItems.length,
          OriginalTime: this.OriginalTime,
          TokenPairID: this.SelectedTokenPairID
        },
        {
          Error: {
            Title: 'Get Kpoints Histories',
            Message: 'Failed to get kpoints histories',
            Popup: true,
            Type: NotifyType.Error
          }
        },
        (resp: GetKPointsForLineResponse): void => {
          if (resp.KPoints.length > 0) {
            this._refreshEchartKPoints(resp.KPoints, true)
          }
          if (this.OriginalTime === 0 && resp.KPoints.length > 0) {
            this.OriginalTime = resp.KPoints[0].Times[1] + 1
          }

          done?.(false, resp.KPoints)
        }, () => {
          done?.(true, [])
        }
      )

      setTimeout(() => {
        this.RefreshKlineHistoryLock = false
      }, 300)
    },
    _refreshEchartKPoints (infos: KPoint[], unshift: boolean) {
      for (let i = 0; i < infos.length; i++) {
        if (unshift) {
          this.EchartPoinsData.CategoryItems.unshift(infos[i].FormatTimes[0])
          this.EchartPoinsData.Nums.unshift(infos[i].Nums)
        } else {
          this.EchartPoinsData.CategoryItems.push(infos[i].FormatTimes[0])
          this.EchartPoinsData.Nums.push(infos[i].Nums)
        }
      }
    }
  }
})
