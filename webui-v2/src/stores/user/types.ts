export enum WalletType {
  NotConnected = 'Not Connected',
  Metamask = 'Metamask',
  CheCko = 'CheCko Wallet',
}

export const WalletTypes = Object.values(WalletType).filter(
  (el) => el !== WalletType.NotConnected,
) as WalletType[]

export enum WalletCookie {
  WalletLoginAccount = 'Wallet-Login-Account',
  WalletLoginMicrochain = 'Wallet-Login-Microchain',
  WalletConnectType = 'Wallet-Connect-Type',
}
