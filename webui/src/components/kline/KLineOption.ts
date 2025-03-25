import * as echarts from 'echarts/core'
import {
  ToolboxComponent,
  ToolboxComponentOption,
  TooltipComponent,
  TooltipComponentOption,
  GridComponent,
  GridComponentOption,
  VisualMapComponent,
  VisualMapComponentOption,
  LegendComponent,
  LegendComponentOption,
  BrushComponent,
  BrushComponentOption,
  DataZoomComponent,
  DataZoomComponentOption
} from 'echarts/components'
import {
  CandlestickChart,
  CandlestickSeriesOption,
  LineChart,
  LineSeriesOption,
  BarChart,
  BarSeriesOption
} from 'echarts/charts'
import { UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'
import { kline } from 'src/localstore'

echarts.use([
  ToolboxComponent,
  TooltipComponent,
  GridComponent,
  VisualMapComponent,
  LegendComponent,
  BrushComponent,
  DataZoomComponent,
  CandlestickChart,
  LineChart,
  BarChart,
  CanvasRenderer,
  UniversalTransition
])

type EChartsOption = echarts.ComposeOption<
  | ToolboxComponentOption
  | TooltipComponentOption
  | GridComponentOption
  | VisualMapComponentOption
  | LegendComponentOption
  | BrushComponentOption
  | DataZoomComponentOption
  | CandlestickSeriesOption
  | LineSeriesOption
  | BarSeriesOption
>

export const calculateMA = (dayCount: number, nums: number[][]) => {
  const result = [] as string[]
  for (let i = 0, len = nums.length; i < len; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    let sum = 0
    for (let j = 0; j < dayCount; j++) {
      sum += nums[i - j][1]
    }
    result.push('' + (sum / dayCount).toFixed(8))
  }
  return result
}

export const calculateZoomStart = (itemsLen: number) => {
  let result = 90
  if (itemsLen < 50) {
    result = 1
  } else {
    result = 100 - 50.0 / itemsLen * 100
  }
  return result
}

const option: EChartsOption = {
  animation: true,
  legend: {
    bottom: 2,
    left: 'center',
    data: ['Index', 'MA5', 'MA10', 'MA20', 'MA30']
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross'
    },
    borderWidth: 1,
    borderColor: '#ccc',
    padding: 10,
    textStyle: {
      color: '#000'
    }
  },
  axisPointer: {
    link: [
      {
        xAxisIndex: 'all'
      }
    ],
    label: {
      backgroundColor: '#777'
    }
  },
  toolbox: {
    feature: {
      dataZoom: {
        yAxisIndex: false
      },
      brush: {
        type: ['lineX', 'clear']
      }
    }
  },
  brush: {
    xAxisIndex: 'all',
    brushLink: 'all',
    outOfBrush: {
      colorAlpha: 0.1
    }
  },
  visualMap: {
    show: false,
    seriesIndex: 5,
    dimension: 2,
    pieces: [
      {
        value: 1,
        color: '#ec0000'
      },
      {
        value: -1,
        color: '#00da3c'
      }
    ]
  },
  grid: [
    {
      left: 2,
      right: 2,
      height: '78%'
    }
  ],
  xAxis: [
    {
      type: 'category',
      // data: data.categoryData,
      boundaryGap: true,
      axisLine: { onZero: false },
      splitLine: { show: false },
      min: 'dataMin',
      max: 'dataMax',
      axisPointer: {
        z: 100
      }
    }
  ],
  yAxis: [
    {
      axisLabel: {
        show: false
      },
      scale: true,
      splitArea: {
        show: true
      },
      boundaryGap: ['5%', '5%']
    }
  ],
  dataZoom: [
    {
      type: 'inside',
      xAxisIndex: [0],
      // start: calculateZoomStart(data.CategoryItems.length),
      end: 100
    },
    {
      show: true,
      xAxisIndex: [0],
      type: 'slider',
      // top: '88%',
      bottom: 35,
      // start: calculateZoomStart(data.CategoryItems.length)
      end: 100
    }
  ],
  series: [
    {
      name: 'Index',
      type: 'candlestick',
      // data: data.values,
      itemStyle: {
        color: '#00da3c',
        color0: '#ec0000',
        borderColor: undefined,
        borderColor0: undefined
      }
    },
    {
      name: 'MA5',
      type: 'line',
      // data: calculateMA(5, data),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA10',
      type: 'line',
      // data: calculateMA(10, data),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA20',
      type: 'line',
      // data: calculateMA(20, data),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA30',
      type: 'line',
      // data: calculateMA(30, data),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    }
  ]
}

export const initEchart = (elementID: string): (echarts.ECharts) => {
  const chartDom = document.getElementById(elementID) as HTMLElement
  const myChart = echarts.init(chartDom)
  window.onresize = () => {
    myChart.resize()
  }

  myChart.setOption(
    option,
    true
  )

  return myChart
}

export const setKPointsToEchart = (myChart: echarts.ECharts, data: kline.EchartKPoints) => {
  const addOption = {
    xAxis: [
      {
        data: data.CategoryItems
      }
    ],
    dataZoom: [] as unknown[],
    // dataZoom: [
    //   {
    //     start: calculateZoomStart(data.CategoryItems.length)
    //   },
    //   {
    //     start: calculateZoomStart(data.CategoryItems.length)
    //   }
    // ],
    series: [
      {
        data: data.Nums
      },
      {
        data: calculateMA(5, data.Nums)
      },
      {
        data: calculateMA(10, data.Nums)
      },
      {
        data: calculateMA(20, data.Nums)
      },
      {
        data: calculateMA(30, data.Nums)
      }
    ]
  }

  myChart.setOption(
    addOption
  )

  // setStartAndEnd(myChart, calculateZoomStart(data.CategoryItems.length), 100)

  // if (data.CategoryItems.length > 20) {
  //   myChart.dispatchAction({
  //     type: 'brush',
  //     areas: [
  //       {
  //         brushType: 'lineX',
  //         coordRange: [data.CategoryItems[data.CategoryItems.length - 20], data.CategoryItems[data.CategoryItems.length - 1]],
  //         xAxisIndex: 0
  //       }
  //     ]
  //   })
  // }
}

export const setStartAndEnd = (myChart: echarts.ECharts, start: number, end: number) => {
  const addOption = {
    dataZoom: [
      {
        start: start,
        end: end
      },
      {
        start: start,
        end: end
      }
    ]
  }
  myChart.setOption(
    addOption
  )
}
