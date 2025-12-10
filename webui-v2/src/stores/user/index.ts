import { defineStore } from 'pinia'
import { dbModel } from '../../model'
import { Account, _Account } from '../account'

export class User {
  static ownerAccount = async () => {
    const user = useUserStore()
    return {
      chain_id: user.chainId,
      owner: _Account.formalizeOwner(
        await dbModel.ownerFromPublicKey(user.publicKey)
      )
    } as Account
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    publicKey: undefined as unknown as string,
    chainId: undefined as unknown as string,
    username: undefined as unknown as string,
    accountBalance: '0.',
    chainBalance: '0.'
  }),
  getters: {
    account(): () => Promise<Account> {
      return async () => {
        if (!this.publicKey)
          return {
            chain_id: this.chainId
          }
        return {
          chain_id: this.chainId,
          owner: _Account.formalizeOwner(
            await dbModel.ownerFromPublicKey(this.publicKey)
          )
        }
      }
    }
  },
  actions: {}
})
