import { NotifyType } from '../notify'
import { useAmsStore } from './store'
import { type Application } from './types'

const ams = useAmsStore()

export class Ams {
  static getApplications = (
    createdAfter?: number,
    done?: (error: boolean, rows?: Application[]) => void,
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
            Type: NotifyType.Error,
          },
        },
      },
      (error: boolean, rows?: Application[]) => {
        if (error || !rows?.length) return done?.(error, rows)
        Ams.getApplications(Math.max(...rows.map((el) => el.createdAt)), done)
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
