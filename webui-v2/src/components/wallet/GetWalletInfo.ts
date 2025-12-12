import { type MetaMaskInpageProvider } from '@metamask/providers'
import { Cookies } from 'quasar'
import { BALANCES } from 'src/graphql'
import { dbModel, rpcModel } from 'src/model'
import { account, user } from 'src/stores/export'
import { Web3 } from 'web3'

export const getCheCkoBalances = async (provider: MetaMaskInpageProvider) => {
  const publicKey = user.User.publicKey()
  const chainId = user.User.chainId()

  if (!publicKey) return
  const owner = await dbModel.ownerFromPublicKey(publicKey)
  provider.request({
    method: 'linera_graphqlQuery',
    params: {
      publicKey,
      query: {
        query: BALANCES.loc?.source?.body,
        variables: {
          chainOwners: [{
            chainId,
            owners: [account._Account.formalizeOwner(owner)]
          }],
          chainId,
          publicKey
        }
      }
    }
  }).then((result) => {
    const balances = result as rpcModel.Balances
    user.User.setChainBalance(rpcModel.chainBalance(balances, chainId))
    user.User.setAccountBalance(rpcModel.ownerBalance(balances, chainId, account._Account.formalizeOwner(owner)))
  }).catch((e) => {
    console.log(e)
  })
}

export const getMetamaskBalance = async (provider: MetaMaskInpageProvider) => {
  const publicKey = user.User.publicKey()

  const web3 = new Web3(provider)
  const balanceWei = await web3.eth.getBalance(publicKey)
  const balanceEth = Number(web3.utils.fromWei(balanceWei, 'ether')).toFixed(4)

  user.User.setAccountBalance(balanceEth)
}

export const getProviderState = (provider: MetaMaskInpageProvider, walletType: user.WalletConnectType, error?: () => void) => {
  console.log(`Connecting wallet ${walletType} ...`)

  provider.request({
    method: 'metamask_getProviderState'
  }).then(async (result) => {
    if (!((result as Record<string, string>)?.accounts)?.length) {
      return error?.()
    }

    user.User.setChainId(((result as Record<string, string>)?.chainId)?.substring(2) as string)
    user.User.setPublicKey(((result as Record<string, string>)?.accounts)?.[0] as string)
    user.User.setWalletConnectedType(walletType)

    Cookies.set('CheCko-Login-Account', user.User.publicKey())
    Cookies.set('CheCko-Login-Microchain', user.User.chainId())
    void (walletType === user.WalletConnectType.CheCko ? await getCheCkoBalances(provider) : await getMetamaskBalance(provider))
  }).catch((e) => {
    console.log('metamask_getProviderState', e)
    error?.()
  })
}

export const walletReadyCall = (f: () => void) => {
  if (!window.linera && !window.ethereum) {
    return setTimeout(() => walletReadyCall(f), 1000)
  }
  f()
}