import { type Chain } from 'src/__generated__/graphql/proxy/graphql'
import { NotifyType } from '../notify'
import { useProxyStore } from './store'

const proxy = useProxyStore()

export const getMemeApplications = (
  done?: (error: boolean, rows?: Chain[]) => void
) => {
  proxy.getApplications(
    {
      Message: {
        Error: {
          Title: 'Get meme applications',
          Message: 'Failed get meme applications',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    done
  )
}
