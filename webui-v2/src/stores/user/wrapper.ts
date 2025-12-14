import { useUserStore } from './store'
import { type Account, _Account } from '../account'
import { dbModel } from 'src/model'
import { type WalletType } from './types'

const user = useUserStore()

export class User {
  static setChainId = (chainId: string) => (user.chainId = chainId)
  static setPublicKey = (publicKey: string) => (user.publicKey = publicKey)
  static setChainBalance = (balance: string) => (user.chainBalance = balance)
  static setAccountBalance = (balance: string) => (user.accountBalance = balance)
  static setWalletConnectedType = (walletType: WalletType) => (user.walletType = walletType)
  static setWalletConnecting = (connecting: boolean) => user.connecting = connecting

  static chainId = () => user.chainId
  static publicKey = () => user.publicKey
  static chainBalance = () => user.chainBalance
  static accountBalance = () => user.accountBalance
  static balance = () => (Number(user.chainBalance) + Number(user.accountBalance)).toString()
  static walletConnected = () => user.chainId !== undefined && user.publicKey !== undefined
  static walletConnecting = () => user.connecting
  static account = async () => await user.account()
  static walletConnectedType = () => user.walletType
}
