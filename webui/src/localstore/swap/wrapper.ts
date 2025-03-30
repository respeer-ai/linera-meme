import { Pool } from 'src/__generated__/graphql/swap/graphql'
import { NotifyType } from '../notify'
import { useSwapStore } from './store'

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
