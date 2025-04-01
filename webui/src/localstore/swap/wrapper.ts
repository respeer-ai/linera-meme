import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { NotifyType } from '../notify'
import { useSwapStore } from './store'
import { Account } from '../account'

const swap = useSwapStore()

export const getPools = (done?: (error: boolean, rows?: Pool[]) => void) => {
  swap.getPools(
    {
      Message: {
        Error: {
          Title: 'Get pools',
          Message: 'Failed get pools',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    done
  )
}

export const createPool = (
  token0: string,
  token1: string | undefined,
  amount0: string,
  amount1: string,
  to: Account | undefined, // TODO: should be a string ?
  done?: (error: boolean) => void
) => {
  swap.createPool(
    {
      token0,
      token1,
      amount0,
      amount1,
      to,
      Message: {
        Error: {
          Title: 'Create pool',
          Message: 'Failed create pool',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    done
  )
}
