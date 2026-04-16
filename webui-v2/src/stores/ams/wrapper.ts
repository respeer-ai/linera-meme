import { NotifyType } from '../notify'
import { useAmsStore } from './store'
import { type Application } from './types'
import {
  resolveApplicationsQueryCreatedAfter,
  resolveNextApplicationsCursor,
} from './pagination'

const ams = useAmsStore()

export class Ams {
  static getApplications = (
    createdAfter?: number,
    done?: (error: boolean, rows?: Application[]) => void,
  ) => {
    ams.getApplications(
      {
        createdAfter: resolveApplicationsQueryCreatedAfter(createdAfter) as number,
        limit: 800,
        Message: {
          Error: {
            Title: 'Get applications',
            Message: 'Failed get applications',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      (error: boolean, rows?: Application[]) => {
        if (error || !rows?.length) return done?.(error, rows)
        const nextCreatedAfter = resolveNextApplicationsCursor(createdAfter, rows)
        if (nextCreatedAfter === undefined) return done?.(false, rows)
        Ams.getApplications(nextCreatedAfter, done)
      },
    )
  }

  static application = (applicationId: string) => {
    return ams.applications.find((el) => el.applicationId === applicationId)
  }

  static applicationLogo = (application: Application) => {
    return ams.applicationLogo(application)
  }

  static applications = () => {
    return ams.applications
  }

  static initialize = () => ams.initializeAms()

  static blockHash = () => ams.blockHash

  static existMeme = (name?: string, ticker?: string) => ams.existMeme(name, ticker)
}
