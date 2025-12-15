import { user } from 'src/stores/export'
import * as linera from '@linera/client'
import * as metamask from '@linera/metamask'
import { Provider } from './provider'
import { stringify } from 'lossless-json'
import { SWAP } from 'src/graphql'
import { print } from 'graphql'

export class LineraWebClient {
  static wallet: linera.Wallet
  static client: linera.Client

  static _connect = async () => {
    if (!window.ethereum) {
      return window.open(
        'https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn?hl=zh-CN&utm_source=ext_sidebar',
      )
    }

    const signer = new metamask.Signer()
    const owner = await signer.address()

    await linera.initialize()

    const faucet = new linera.Faucet('https://faucet.testnet-conway.linera.net')
    LineraWebClient.wallet = await faucet.createWallet()
    const chain = await faucet.claimChain(LineraWebClient.wallet, owner)

    // eslint-disable-next-line @typescript-eslint/await-thenable
    LineraWebClient.client = await new linera.Client(LineraWebClient.wallet, signer, false)

    LineraWebClient.getProviderState(() => {
      user.User.setChainId(chain)
    })
  }

  static connect = async (success?: () => void, error?: (e: string) => void) => {
    try {
      await LineraWebClient._connect()
      success?.()
    } catch (e: unknown) {
      error?.(e as string)
    }
  }

  static subscribe = (onData: (walletType: user.WalletType, msg: unknown) => void) => {
    LineraWebClient.client?.onNotification((notification: unknown) => {
      onData(user.WalletType.Metamask, notification)
    })
  }

  static getProviderState = (onConnected?: () => void, onBalance?: () => void, error?: () => void) => {
    if (!window.ethereum) {
      return error?.()
    }
    Provider.getProviderState(
      window.ethereum,
      async () => {
        user.User.setWalletConnectedType(user.WalletType.Metamask)
        onConnected?.()
        if (!LineraWebClient.client) {
          await LineraWebClient.connect()
          await LineraWebClient.getBalance()
          return onBalance?.()
        }
        await LineraWebClient.getBalance()
        onBalance?.()
      },
      error,
    )
  }

  static getBalance = async () => {
    if (!LineraWebClient.client) return

    try {
      const accountBalance = await LineraWebClient.client.balance()

      user.User.setChainBalance(accountBalance)
    } catch (e) {
      console.log('Failed get balance: ', e)
      window.setTimeout(() => void LineraWebClient.getBalance(), 5000)
    }
  }

  static swap = async (poolApplicationId: string, variables: Record<string, unknown>) => {
    const application = await LineraWebClient.client.application(poolApplicationId)
    const gqlStr = stringify({
      query: print(SWAP),
      variables,
    }) as string
    await application.query(gqlStr)
  }

  static createMeme = async (
    argument: unknown,
    parameters: unknown,
    variables: Record<string, unknown>,
  ) => {
    console.log(argument, parameters, variables)
    return Promise.reject(new Error('Not implemented'))
  }
}
