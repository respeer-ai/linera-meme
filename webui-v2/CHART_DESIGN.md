# 专业交易图表设计方案

## 📊 参考标准：Raydium / TradingView 级别图表

### 一、核心功能需求

#### 1. 图表工具栏（Chart Toolbar）

```
┌─────────────────────────────────────────────────────────────┐
│ [蜡烛图▼] [指标▼] [1m][5m][15m][1h][4h][1d] [🔧] [⚙️] [📷] │
└─────────────────────────────────────────────────────────────┘
```

**1.1 图表类型切换**

- 蜡烛图（Candlestick）- 默认
- 折线图（Line）
- 面积图（Area）
- 柱状图（Bars）
- Heikin-Ashi
- Hollow Candles

**1.2 时间周期（Timeframe）**

- 1m, 3m, 5m, 15m, 30m
- 1h, 2h, 4h, 6h, 12h
- 1d, 1w, 1M

**1.3 技术指标（Indicators）**
主图指标：

- MA（移动平均线）- 可配置周期
- EMA（指数移动平均）
- BOLL（布林带）
- SAR（抛物线转向）

副图指标：

- Volume（成交量）- 默认显示
- MACD
- RSI
- KDJ
- OBV

**1.4 绘图工具（Drawing Tools）**

- 趋势线
- 水平线/垂直线
- 矩形/圆形
- 斐波那契回调
- 文本标注

**1.5 其他功能**

- 全屏模式
- 截图保存
- 设置面板
- 重置图表

---

### 二、架构设计

#### 2.1 组件结构

```
components/chart/
├── ChartContainer.vue          # 图表容器（主组件）
├── toolbar/
│   ├── ChartToolbar.vue       # 工具栏主组件
│   ├── ChartTypeSelector.vue  # 图表类型选择器
│   ├── IntervalSelector.vue   # 时间周期选择器
│   ├── IndicatorSelector.vue  # 指标选择器
│   ├── DrawingTools.vue       # 绘图工具
│   └── ChartSettings.vue      # 设置面板
├── chart/
│   ├── MainChart.vue          # 主图表（价格）
│   ├── VolumeChart.vue        # 成交量图
│   ├── IndicatorChart.vue     # 副图指标
│   └── ChartOverlay.vue       # 图表覆盖层（OHLCV显示）
├── indicators/
│   ├── MA.ts                  # 移动平均线
│   ├── EMA.ts                 # 指数移动平均
│   ├── BOLL.ts                # 布林带
│   ├── MACD.ts                # MACD
│   ├── RSI.ts                 # RSI
│   └── index.ts               # 指标注册中心
└── types/
    ├── chart.ts               # 图表类型定义
    ├── indicator.ts           # 指标类型定义
    └── drawing.ts             # 绘图类型定义
```

#### 2.2 状态管理

```typescript
// stores/chart/store.ts
interface ChartState {
  // 图表配置
  chartType: ChartType // 当前图表类型
  interval: Interval // 当前时间周期

  // 指标配置
  mainIndicators: IndicatorConfig[] // 主图指标（MA, BOLL等）
  subIndicators: IndicatorConfig[] // 副图指标（MACD, RSI等）

  // 数据
  klineData: KLineData[] // K线数据
  loading: boolean // 加载状态

  // 视图配置
  showVolume: boolean // 显示成交量
  showGrid: boolean // 显示网格
  showCrosshair: boolean // 显示十字线

  // 主题配置
  theme: 'dark' | 'light'
  colors: ChartColors

  // 绘图
  drawings: Drawing[] // 用户绘制的图形
}
```

#### 2.3 数据流

```
用户操作 → ChartToolbar → ChartStore → ChartContainer
                                ↓
                          数据加载/计算
                                ↓
                    MainChart + IndicatorChart
                                ↓
                          渲染到 Canvas
```

---

### 三、技术实现方案

#### 3.1 图表库选择

**当前使用：lightweight-charts**

- ✅ 轻量级，性能好
- ✅ 已集成
- ❌ 功能相对简单
- ❌ 绘图工具支持有限

**升级方案：**

**方案A：继续使用 lightweight-charts + 自定义扩展**

- 优点：无需重构，渐进式增强
- 缺点：需要大量自定义开发
- 适用：中小型项目

**方案B：集成 TradingView Charting Library**

- 优点：功能完整，专业级
- 缺点：商业授权，体积大
- 适用：商业项目

**方案C：使用 Kline-Chart**

- 优点：开源，功能丰富，中文文档
- 缺点：需要重构现有代码
- 适用：追求功能完整性

**推荐：方案A（渐进式增强）**

#### 3.2 指标计算

```typescript
// stores/chart/indicators.ts
export class IndicatorCalculator {
  // 移动平均线
  static calculateMA(data: number[], period: number): number[] {
    const result: number[] = []
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        result.push(NaN)
      } else {
        const sum = data.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0)
        result.push(sum / period)
      }
    }
    return result
  }

  // MACD
  static calculateMACD(data: number[], fast = 12, slow = 26, signal = 9) {
    const emaFast = this.calculateEMA(data, fast)
    const emaSlow = this.calculateEMA(data, slow)
    const dif = emaFast.map((v, i) => v - emaSlow[i])
    const dea = this.calculateEMA(dif, signal)
    const macd = dif.map((v, i) => (v - dea[i]) * 2)
    return { dif, dea, macd }
  }

  // RSI
  static calculateRSI(data: number[], period = 14): number[] {
    // RSI 计算逻辑
  }

  // 布林带
  static calculateBOLL(data: number[], period = 20, multiplier = 2) {
    const ma = this.calculateMA(data, period)
    const std = this.calculateStdDev(data, period)
    const upper = ma.map((v, i) => v + multiplier * std[i])
    const lower = ma.map((v, i) => v - multiplier * std[i])
    return { upper, middle: ma, lower }
  }
}
```

#### 3.3 响应式时间周期

```typescript
// 根据时间周期动态调整
const chartConfig = computed(() => {
  const interval = selectedInterval.value

  return {
    // 数据窗口
    windowSize: getWindowSize(interval),

    // 最大数据点
    maxPoints: getMaxPoints(interval),

    // MA 周期
    maPeriods: getDefaultMAPeriods(interval),

    // 时间格式
    timeFormat: getTimeFormat(interval),

    // 价格精度
    pricePrecision: getPricePrecision(interval),
  }
})

function getDefaultMAPeriods(interval: Interval) {
  switch (interval) {
    case Interval.ONE_MINUTE:
    case Interval.FIVE_MINUTE:
      return [5, 10, 30]
    case Interval.ONE_HOUR:
    case Interval.FOUR_HOUR:
      return [7, 25, 99]
    case Interval.ONE_DAY:
      return [7, 30, 120]
    default:
      return [5, 10, 30]
  }
}
```

---

### 四、UI/UX 设计

#### 4.1 工具栏布局

```vue
<template>
  <div class="chart-toolbar row items-center q-px-md q-py-xs bg-dark-secondary">
    <!-- 左侧：图表类型 + 指标 -->
    <div class="row items-center q-gutter-sm">
      <chart-type-selector v-model="chartType" />
      <indicator-selector v-model="indicators" />
    </div>

    <q-space />

    <!-- 中间：时间周期 -->
    <div class="row items-center q-gutter-xs">
      <q-btn
        v-for="interval in intervals"
        :key="interval.value"
        :label="interval.label"
        :unelevated="selectedInterval === interval.value"
        :outline="selectedInterval !== interval.value"
        dense
        no-caps
        size="sm"
        @click="selectedInterval = interval.value"
      />
    </div>

    <q-space />

    <!-- 右侧：工具 -->
    <div class="row items-center q-gutter-xs">
      <q-btn icon="draw" flat dense round>
        <q-menu>
          <drawing-tools />
        </q-menu>
      </q-btn>
      <q-btn icon="settings" flat dense round @click="showSettings = true" />
      <q-btn icon="fullscreen" flat dense round @click="toggleFullscreen" />
      <q-btn icon="camera_alt" flat dense round @click="takeScreenshot" />
    </div>
  </div>
</template>
```

#### 4.2 图表信息显示

```vue
<!-- 悬停信息 -->
<div class='chart-overlay absolute-top-left q-pa-sm'>
  <div class='row items-center q-gutter-md text-caption'>
    <span class='text-grey-5'>{{ formatTime(hoveringTime) }}</span>
    <span :class='priceChangeClass'>O {{ formatPrice(open) }}</span>
    <span :class='priceChangeClass'>H {{ formatPrice(high) }}</span>
    <span :class='priceChangeClass'>L {{ formatPrice(low) }}</span>
    <span :class='priceChangeClass'>C {{ formatPrice(close) }}</span>
    <span class='text-grey-5'>V {{ formatVolume(volume) }}</span>
  </div>

  <!-- 指标数值 -->
  <div class='row items-center q-gutter-md text-caption q-mt-xs'>
    <span v-for='indicator in activeIndicators' :key='indicator.name'>
      <span :style='{ color: indicator.color }'>
        {{ indicator.name }}({{ indicator.params.join(',') }})
      </span>
      <span class='q-ml-xs'>{{ formatIndicatorValue(indicator) }}</span>
    </span>
  </div>
</div>
```

#### 4.3 主题配置

```typescript
// Dark Theme (默认)
const darkTheme = {
  background: '#131722',
  textColor: '#d9d9d9',
  gridColor: 'rgba(42, 46, 57, 0.5)',
  upColor: '#26a69a', // 涨
  downColor: '#ef5350', // 跌
  volumeUpColor: 'rgba(38, 166, 154, 0.5)',
  volumeDownColor: 'rgba(239, 83, 80, 0.5)',
  ma5Color: '#FFA500', // 橙色
  ma10Color: '#00BFFF', // 蓝色
  ma30Color: '#32CD32', // 绿色
  crosshairColor: '#758696',
}

// Light Theme
const lightTheme = {
  background: '#ffffff',
  textColor: '#191919',
  gridColor: 'rgba(197, 203, 206, 0.5)',
  upColor: '#089981',
  downColor: '#f23645',
  // ...
}
```

---

### 五、实施计划

#### Phase 1: 重构基础架构（2-3天）

- [ ] 创建新的组件结构
- [ ] 重构状态管理
- [ ] 实现图表类型切换
- [ ] 优化时间周期切换逻辑

#### Phase 2: 指标系统（2-3天）

- [ ] 实现指标计算引擎
- [ ] 添加主图指标（MA, EMA, BOLL）
- [ ] 添加副图指标（MACD, RSI, KDJ）
- [ ] 指标配置面板

#### Phase 3: 交互增强（2天）

- [ ] 优化工具栏布局
- [ ] 改进悬停信息显示
- [ ] 添加全屏模式
- [ ] 添加截图功能

#### Phase 4: 高级功能（3-4天）

- [ ] 绘图工具（趋势线、水平线等）
- [ ] 多时间周期对比
- [ ] 图表同步
- [ ] 性能优化

#### Phase 5: 测试与优化（1-2天）

- [ ] 功能测试
- [ ] 性能测试
- [ ] 移动端适配
- [ ] 文档完善

**总计：10-14天**

---

### 六、关键技术点

#### 6.1 性能优化

- 使用 Web Worker 计算指标
- 虚拟滚动加载历史数据
- Canvas 渲染优化
- 数据缓存策略

#### 6.2 数据管理

- IndexedDB 持久化
- 增量更新机制
- 数据压缩存储
- 智能预加载

#### 6.3 扩展性

- 插件化指标系统
- 可配置的图表主题
- 自定义绘图工具
- API 友好的接口设计

---

### 七、与现有代码的兼容性

**保持兼容：**

- 继续使用 lightweight-charts
- 保持现有的数据流
- 渐进式重构，不影响现有功能

**升级路径：**

1. 先完成工具栏和时间周期优化
2. 逐步添加指标功能
3. 最后添加绘图工具

---

## 参考资源

- [TradingView Charting Library](https://www.tradingview.com/HTML5-stock-forex-bitcoin-charting-library/)
- [Lightweight Charts Documentation](https://tradingview.github.io/lightweight-charts/)
- [Kline-Chart](https://github.com/liihuu/KLineChart)
- [Technical Analysis Library](https://github.com/anandanand84/technicalindicators)

---

## 下一步行动

请确认以下问题：

1. **优先级**：你最需要哪些功能？
   - [ ] 完整的时间周期支持
   - [ ] 技术指标（MA, MACD, RSI等）
   - [ ] 图表类型切换
   - [ ] 绘图工具
   - [ ] 全部功能

2. **时间预算**：可以投入多少开发时间？
   - [ ] 快速实现（3-5天，核心功能）
   - [ ] 完整实现（10-14天，全功能）

3. **技术选择**：
   - [ ] 继续使用 lightweight-charts（推荐）
   - [ ] 切换到其他图表库

确认后我将开始实施！
