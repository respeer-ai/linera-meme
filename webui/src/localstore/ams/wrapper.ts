import { NotifyType } from '../notify'
import { useAmsStore } from './store'
import { Application } from './types'

const ams = useAmsStore()

export const getApplications = (
  done?: (error: boolean, rows?: Application[]) => void
) => {
  ams.getApplications(
    {
      limit: 40,
      Message: {
        Error: {
          Title: 'Get applications',
          Message: 'Failed get applications',
          Popup: true,
          Type: NotifyType.Error
        }
      }
    },
    done
  )
}
