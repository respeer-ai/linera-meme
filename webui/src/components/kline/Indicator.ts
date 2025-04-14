import { Indicator, IndicatorFigure, KLineData } from 'klinecharts'

interface Vol {
  open: number
  close: number
  volume?: number
  ma1?: number
  ma2?: number
  ma3?: number
}

interface Ma {
  ma1?: number
  ma2?: number
  ma3?: number
  ma4?: number
}

const reEscapeChar = /\\(\\)?/g
const rePropName = RegExp(
  '[^.[\\]]+' +
    '|' +
    '\\[(?:' +
    '([^"\'][^[]*)' +
    '|' +
    '(["\'])((?:(?!\\2)[^\\\\]|\\\\.)*?)\\2' +
    ')\\]' +
    '|' +
    '(?=(?:\\.|\\[\\])(?:\\.|\\[\\]|$))',
  'g'
)

export class _Indicator {
  static movingAverage = {
    name: 'MA',
    shortName: 'MA',
    series: 'price',
    calcParams: [5, 10, 30, 60],
    precision: 10,
    shouldOhlc: true,
    figures: [
      { key: 'ma1', title: 'MA5: ', type: 'line' },
      { key: 'ma2', title: 'MA10: ', type: 'line' },
      { key: 'ma3', title: 'MA30: ', type: 'line' },
      { key: 'ma4', title: 'MA60: ', type: 'line' }
    ],
    regenerateFigures: (params: number[]) =>
      params.map((p, i) => ({
        key: `ma${i + 1}`,
        title: `MA${p}: `,
        type: 'line'
      })),
    calc: (dataList: KLineData[], indicator: Indicator) => {
      const { calcParams: params, figures } = indicator
      const closeSums: number[] = []
      return dataList.map((kLineData, i) => {
        const ma = {} as Ma
        const close = kLineData.close
        params.forEach((p, index) => {
          closeSums[index] = (closeSums[index] ?? 0) + close
          const _p = p as number
          if (i >= _p - 1) {
            ma[figures[index].key] = closeSums[index] / _p
            closeSums[index] -= dataList[i - (_p - 1)].close
          }
        })
        return ma
      })
    }
  }

  static exponentialMovingAverate = {
    name: 'EMA',
    shortName: 'EMA',
    series: 'price',
    calcParams: [5, 10, 30, 60],
    precision: 10,
    shouldOhlc: true,
    figures: [
      { key: 'ema1', title: 'EMA5: ', type: 'line' },
      { key: 'ema2', title: 'EMA10: ', type: 'line' },
      { key: 'ema3', title: 'EMA30: ', type: 'line' },
      { key: 'ema4', title: 'EMA60: ', type: 'line' }
    ],
    regenerateFigures: (params: number[]) =>
      params.map((p, i) => ({
        key: `ema${i + 1}`,
        title: `EMA${p}: `,
        type: 'line'
      })),
    calc: (dataList: KLineData[], indicator: Indicator) => {
      const { calcParams: params, figures } = indicator
      let closeSum = 0
      const emaValues: number[] = []
      return dataList.map((kLineData, i) => {
        const ema = {}
        const close = kLineData.close
        closeSum += close
        params.forEach((p, index) => {
          const _p = p as number
          if (i >= _p - 1) {
            if (i > _p - 1) {
              emaValues[index] =
                (2 * close + (_p - 1) * emaValues[index]) / (_p + 1)
            } else {
              emaValues[index] = closeSum / _p
            }
            ema[figures[index].key] = emaValues[index]
          }
        })
        return ema
      })
    }
  }

  static isValid<T>(value: T | null | undefined): value is T {
    return value !== null && value !== undefined
  }

  static formatValue = (data: unknown, key: string, defaultValue?: unknown) => {
    if (_Indicator.isValid(data)) {
      const path: string[] = []
      key.replace(rePropName, (subString: string, ...args: unknown[]) => {
        let k = subString
        if (_Indicator.isValid(args[1])) {
          k = (args[2] as string).replace(reEscapeChar, '$1')
        } else if (_Indicator.isValid(args[0])) {
          k = (args[0] as string).trim()
        }
        path.push(k)
        return ''
      })
      let value = data
      let index = 0
      const length = path.length
      while (_Indicator.isValid(value) && index < length) {
        value = value?.[path[index++]]
      }
      return _Indicator.isValid(value) ? value : (defaultValue ?? '--')
    }
    return defaultValue ?? '--'
  }

  static getVolumeFigure(): IndicatorFigure<Vol> {
    return {
      key: 'volume',
      title: 'VOLUME: ',
      type: 'bar',
      baseValue: 0,
      styles: ({ data, indicator, defaultStyles }) => {
        const current = data.current
        let color = _Indicator.formatValue(
          indicator.styles,
          'bars[0].noChangeColor',
          defaultStyles?.bars?.[0].noChangeColor
        )
        if (_Indicator.isValid(current)) {
          if (current.close > current.open) {
            color = _Indicator.formatValue(
              indicator.styles,
              'bars[0].upColor',
              defaultStyles?.bars?.[0].upColor
            )
          } else if (current.close < current.open) {
            color = _Indicator.formatValue(
              indicator.styles,
              'bars[0].downColor',
              defaultStyles?.bars?.[0].downColor
            )
          }
        }
        return { color: color as string }
      }
    }
  }

  static volume = {
    name: 'VOL',
    shortName: 'VOL',
    series: 'volume',
    calcParams: [5, 10, 30, 60],
    shouldFormatBigNumber: true,
    precision: 4,
    minValue: 0,
    figures: [
      { key: 'ma1', title: 'MA5: ', type: 'line' },
      { key: 'ma2', title: 'MA10: ', type: 'line' },
      { key: 'ma3', title: 'MA30: ', type: 'line' },
      { key: 'ma4', title: 'MA60: ', type: 'line' },
      _Indicator.getVolumeFigure()
    ],
    regenerateFigures: (params: number[]) => {
      const figures: Array<IndicatorFigure<Vol>> = params.map((p, i) => ({
        key: `ma${i + 1}`,
        title: `MA${p}: `,
        type: 'line'
      }))
      figures.push(_Indicator.getVolumeFigure())
      return figures
    },
    calc: (dataList: KLineData[], indicator: Indicator) => {
      const { calcParams: params, figures } = indicator
      const volSums: number[] = []
      return dataList.map((kLineData, i) => {
        const volume = kLineData.volume ?? 0
        const vol: Vol = {
          volume,
          open: kLineData.open,
          close: kLineData.close
        }
        params.forEach((p, index) => {
          volSums[index] = (volSums[index] ?? 0) + volume
          const _p = p as number
          if (i >= _p - 1) {
            vol[figures[index].key] = volSums[index] / _p
            volSums[index] -= dataList[i - (_p - 1)].volume ?? 0
          }
        })
        return vol
      })
    }
  }
}
