import { type MetaMaskInpageProvider } from '@metamask/providers'
import { Cookies } from 'quasar'
import { user } from 'src/stores/export'

export class Provider {
  static getProviderState = (
    provider: MetaMaskInpageProvider,
    success?: (chainId: string) => void,
    error?: () => void,
  ) => {
    provider
      .request({
        method: 'metamask_getProviderState',
      })
      .then((result) => {
        if (!(result as Record<string, string>)?.accounts?.length) {
          return error?.()
        }

        user.User.setPublicKey((result as Record<string, string>)?.accounts?.[0] as string)

        Cookies.set('Wallet-Login-Account', user.User.publicKey())
        Cookies.set('Wallet-Login-Microchain', user.User.chainId())

        success?.((result as Record<string, string>)?.chainId?.substring(2) as string)
      })
      .catch((e) => {
        console.log('metamask_getProviderState', e)
        error?.()
      })
  }
}
