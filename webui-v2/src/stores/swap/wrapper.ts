import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { NotifyType } from '../notify'
import { useSwapStore } from './store'
import { poolVisibility, protocol } from 'src/utils'

const swap = useSwapStore()

export class Swap {
  static getPools = (done?: (error: boolean, rows?: Pool[]) => void) => {
    swap.getPools(
      {
        Message: {
          Error: {
            Title: 'Get pools',
            Message: 'Failed get pools',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      done,
    )
  }

  static pools = () => swap.pools
  static visiblePools = () => poolVisibility.visiblePools(swap.pools)
  static blockHash = () => swap.blockHash

  static initialize = () => swap.initializeSwap()

  static getPool = (buyToken: string, sellToken: string) => swap.getPool(buyToken, sellToken)
  static getVisiblePool = (buyToken: string, sellToken: string) => {
    const pool = swap.getPool(buyToken, sellToken)
    return pool && poolVisibility.isFinalizedPool(pool) ? pool : undefined
  }
  static selectedPool = () => swap.getPool(swap.buyToken, swap.sellToken)
  static selectedVisiblePool = () => Swap.getVisiblePool(swap.buyToken, swap.sellToken)
  static buyToken = () => swap.buyToken
  static sellToken = () => swap.sellToken

  static setBuyToken = (buyToken: string) => (swap.buyToken = buyToken)
  static setSellToken = (sellToken: string) => (swap.sellToken = sellToken)

  static calculatePriceImpact = (buyToken: string, sellToken: string, _amountIn: string) => {
    const pool = swap.getPool(buyToken, sellToken)
    if (!pool) return '0'

    const reserveIn = Number(sellToken === pool.token0 ? pool.reserve0 : pool.reserve1)
    const reserveOut = Number(buyToken === pool.token0 ? pool.reserve0 : pool.reserve1)
    const amountIn = Number(_amountIn)
    return Number(protocol.calculateConstantProductPriceImpact(reserveIn, reserveOut, amountIn))
      .toFixed(8)
      .toString()
  }

  static tokenPrice = (token: string) => {
    const nativePriceMap = protocol.buildNativePriceMap(Swap.visiblePools())
    return (nativePriceMap.get(token) || 0).toFixed(8)
  }

  static poolTvl = (pool: Pool) => {
    const nativePriceMap = protocol.buildNativePriceMap(Swap.visiblePools())
    const tvl = protocol.calculatePoolTvlInNative(pool, nativePriceMap)
    return tvl === undefined ? undefined : tvl.toFixed(8)
  }
}
