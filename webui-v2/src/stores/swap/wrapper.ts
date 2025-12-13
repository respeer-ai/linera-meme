import { type Pool } from 'src/__generated__/graphql/swap/graphql'
import { NotifyType } from '../notify'
import { useSwapStore } from './store'
import { type Account } from '../account'

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

  static createPool = (
    token0: string,
    token1: string | undefined,
    amount0: string,
    amount1: string,
    to: Account | undefined, // TODO: should be a string ?
    done?: (error: boolean) => void,
  ) => {
    swap.createPool(
      {
        token0,
        token1: token1 as string,
        amount0,
        amount1,
        to: to as Account,
        Message: {
          Error: {
            Title: 'Create pool',
            Message: 'Failed create pool',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      done,
    )
  }

  static pools = () => swap.pools
  static blockHash = () => swap.blockHash

  static initialize = () => swap.initializeSwap()
}
