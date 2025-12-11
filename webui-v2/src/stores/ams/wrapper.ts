import { NotifyType } from '../notify'
import { useAmsStore } from './store'
import { type Application } from './types'

const ams = useAmsStore()

export const getApplications = (
  createdAfter?: number,
  done?: (error: boolean, rows?: Application[]) => void
) => {
  ams.getApplications(
    {
      createdAfter: createdAfter as number,
      limit: 800,
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
      getApplications(Math.max(...rows.map((el) => el.createdAt)), done)
    }
  )
}

export const application = (applicationId: string) => {
  return ams.applications.find((el) => el.applicationId === applicationId)
}

export const applicationLogo = (application: Application) => {
  return ams.applicationLogo(application)
}
