import { type Account } from './types'
import { constants } from '../../constant'

export class _Account {
  static CHAIN = '0x00'

  static applicationUrl = (httpBaseUrl: string, application: Account) => {
    if (!application?.owner) return
    const chainId = application.chain_id
    const applicationId = _Account.accountApplication(application) as string
    return constants.formalizeSchema(
      `${httpBaseUrl}/chains/${chainId}/applications/${applicationId}`,
    )
  }

  static accountDescription = (account: Account) => {
    const chainId = _Account.chainId(account)
    const owner = _Account.accountOwner(account) || _Account.CHAIN
    return `${owner}@${chainId}`
  }

  static accountOwner = (account: Account) => {
    if (!account.owner) return
    return _Account.formalizeOwner(account.owner)
  }

  static accountApplication = (account: Account) => {
    if (!account.owner) return
    return account.owner.startsWith('0x') ? account.owner.substring(2) : account.owner
  }

  static formalizeOwner(owner: string) {
    return owner.startsWith('0x') ? owner : `0x${owner}`
  }

  static chainId = (account: Account) => {
    return account.chain_id || account.chainId
  }

  static poolApplicationDescription = (application: Account | undefined) => {
    if (!application?.owner) return
    return _Account.accountDescription(application)
  }

  static fromString = (str: string) => {
    const [owner, chain] = str.includes('@') ? str.split('@', 2) : [_Account.CHAIN, str]
    return {
      chain_id: chain,
      owner: owner === _Account.CHAIN ? undefined : owner,
    } as Account
  }
}

export * from './types'
