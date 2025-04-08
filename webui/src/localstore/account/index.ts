import { Account } from './types'

export class _Account {
  static CHAIN = '0x00'

  static applicationUrl = (
    host: string,
    endpoint: string,
    application: Account
  ) => {
    if (!application.owner) return
    const chainId = application.chainId
    const applicationId = _Account.accountApplication(application) as string
    return `http://${host}/api/${endpoint}/chains/${chainId}/applications/${applicationId}`
  }

  static accountDescription = (account: Account) => {
    let description = account.chainId
    if (account.owner) description += ':' + account.owner
    return description
  }

  static accountOwner = (account: Account) => {
    if (!account.owner) return
    return _Account.formalizeOwner(account.owner)
  }

  static accountApplication = (account: Account) => {
    if (!account.owner) return
    return account.owner.startsWith('0x')
      ? account.owner.substring(2)
      : account.owner
  }

  static formalizeOwner(owner: string) {
    return owner.startsWith('0x') ? owner : `0x${owner}`
  }
}

export * from './types'
