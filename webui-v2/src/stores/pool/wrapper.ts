import { _Account, Account } from '../account'
import { NotifyType } from '../notify'
import { usePoolStore } from './store'
import { LiquidityAmount } from './types'

const pool = usePoolStore()

export const calculateAmountLiquidity = (
  amount0Desired: string,
  amount1Desired: string,
  poolApplication: Account,
  done?: (liquidity?: LiquidityAmount) => void
) => {
  pool.calculateLiquidityAmountPair(
    {
      amount0Desired,
      amount1Desired,
      Message: {
        Error: {
          Title: 'Calculate amount liquidity',
          Message: 'Failed calculate amount liquidity',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    poolApplication,
    (error: boolean, liquidity?: LiquidityAmount) => {
      if (error) return
      done?.(liquidity)
    }
  )
}

export const liquidity = (
  account: Account,
  poolApplication: Account,
  done?: (liquidity?: LiquidityAmount) => void
) => {
  pool.liquidity(
    {
      owner: _Account.accountDescription(account),
      Message: {
        Error: {
          Title: 'Owner liquidity',
          Message: 'Failed get owner liquidity',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    poolApplication,
    (error: boolean, liquidity?: LiquidityAmount) => {
      if (error) return
      done?.(liquidity)
    }
  )
}
