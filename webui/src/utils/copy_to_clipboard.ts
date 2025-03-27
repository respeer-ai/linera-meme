import { notify } from 'src/localstore'
import { copyToClipboard } from 'quasar'

const _notify = notify.useNotificationStore()

export const _copyToClipboard = (
  content: string,
  evt: {
    preventDefault(): unknown
    clipboardData: { getData: (arg0: string) => string }
  }
) => {
  evt.preventDefault()
  copyToClipboard(content)
    .then(() => {
      _notify.pushNotification({
        Title: 'Copy meme token',
        Message: `Success copy ${content.substring(0, 20)}... to clipboard.`,
        Popup: true,
        Type: notify.NotifyType.Info
      })
    })
    .catch((e) => {
      _notify.pushNotification({
        Title: 'Copy meme token',
        // eslint-disable-next-line @typescript-eslint/restrict-template-expressions
        Message: `Failed copy ${content.substring(0, 20)}...: ${e}`,
        Popup: true,
        Type: notify.NotifyType.Error
      })
    })
}
