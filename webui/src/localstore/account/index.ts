import { Account } from './types'

export class _Account {
  static applicationUrl = (application: Account) => {
    if (!application.owner) return
    const chainId = application.chainId
    const applicationId = application.owner.split(':')[1]
    return `http://api.linerameme.fun/api/proxy/chains/${chainId}/applications/${applicationId}`
  }

  static accountDescription = (account: Account) => {
    let description = account.chainId
    if (account.owner) description += ':' + account.owner
    return description
  }
}

export * from './types'
