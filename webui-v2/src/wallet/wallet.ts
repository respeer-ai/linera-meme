import { user } from 'src/stores/export'
import { CheCko } from './checko'
import { LineraWebClient } from './linera_web_client'

export class Wallet {
  static installed = () => {
    return window.linera || window.ethereum
  }

  static waitOnReady = <T extends unknown[]>(f: (...args: T) => void,
    ...args: T
  ) => {
    if (!window.linera && !window.ethereum) {
        return setTimeout(() => Wallet.waitOnReady(f, ...args), 1000)
    }
    f(...args)
  }

  static getProviderState = (walletType: user.WalletType, error?: () => void) => {
    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.getProviderState(() => {}, error)
      case user.WalletType.Metamask:
        return LineraWebClient.getProviderState(() => {}, error)
    }
  }

  static getBalance = (walletType: user.WalletType) => {
    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.getBalance()
      case user.WalletType.Metamask:
        return LineraWebClient.getBalance()
    }
  }

  static connect = async (walletType: user.WalletType, success?: () => void, error?: (e: string) => void) => {
    switch (walletType) {
      case user.WalletType.CheCko:
        return await CheCko.connect(success, error)
      case user.WalletType.Metamask:
        return await LineraWebClient.connect(success, error)
    }
  }

  static subscribe = (walletType: user.WalletType, onSubscribed: (subscriptionId: string) => void, onData: (walletType: user.WalletType, msg: unknown) => void) => {
    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.subscribe(onSubscribed, onData)
      case user.WalletType.Metamask:
        return LineraWebClient.subscribe(onData)
    }
  }

  static unsubscribe = (subscriptionId: string) => {
    CheCko.unsubscribe(subscriptionId)
  }
}
