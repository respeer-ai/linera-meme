import { useUserStore } from './store'
import { type Account, _Account } from '../account'
import { dbModel } from 'src/model'
import { type WalletConnectType } from './types'

const user = useUserStore()

export class User {
  static ownerAccount = async () => {
    return {
      chain_id: user.chainId,
      owner: _Account.formalizeOwner(
        await dbModel.ownerFromPublicKey(user.publicKey)
      )
    } as Account
  }

  static setChainId = (chainId: string) => user.chainId = chainId
  static setPublicKey = (publicKey: string) => user.publicKey = publicKey
  static setChainBalance = (balance: string) => user.chainBalance = balance
  static setAccountBalance = (balance: string) => user.accountBalance = balance
  static setWalletConnectedType = (walletType: WalletConnectType) => user.walletConnectionType = walletType

  static chainId = () => user.chainId
  static publicKey = () => user.publicKey
  static chainBalance = () => user.chainBalance
  static accountBalance = () => user.accountBalance
  static balance = () => (Number(user.chainBalance) + Number(user.accountBalance)).toString()
  static walletConnected = () => user.chainId && user.publicKey
  static account = async () => await user.account()
  static walletConnectedType = () => user.walletConnectionType
}
