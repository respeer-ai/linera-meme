import { NotifyType } from '../notify'
import { useAmsStore } from './store'
import { Application } from './types'

const ams = useAmsStore()

export const getApplications = (
  createdAfter: number,
  done?: (error: boolean, rows?: Application[]) => void
) => {
  ams.getApplications(
    {
      createdAfter,
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
    (error: boolean, rows?: Application[]) => {
      if (error || !rows?.length) return done?.(error, rows)
      getApplications(Math.max(...rows.map((el) => el.createdAt)))
    }
  )
}
