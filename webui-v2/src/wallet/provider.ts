import { type MetaMaskInpageProvider } from '@metamask/providers'
import { Cookies } from 'quasar'
import { user } from 'src/stores/export'

export class Provider {
  static getProviderState = async (
    provider: MetaMaskInpageProvider
  ) => {
    if (!provider) throw new Error('Invalid provider')

    const result = await provider
      .request({
        method: 'metamask_getProviderState',
      })

    if (!(result as Record<string, string>)?.accounts?.length) {
      throw new Error('Invalid account')
    }

    user.User.setPublicKey((result as Record<string, string>)?.accounts?.[0] as string)

    Cookies.set('Wallet-Login-Account', user.User.publicKey())
    Cookies.set('Wallet-Login-Microchain', user.User.chainId())

    return (result as Record<string, string>)?.chainId?.substring(2) as string
  }
}
