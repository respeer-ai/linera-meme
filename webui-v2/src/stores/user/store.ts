import { defineStore } from 'pinia'
import { dbModel } from '../../model'
import { type Account, _Account } from '../account'
import { WalletType } from './types'

export const useUserStore = defineStore('user', {
  state: () => ({
    publicKey: undefined as unknown as string,
    chainId: undefined as unknown as string,
    accountBalance: '0.',
    chainBalance: '0.',
    walletType: WalletType.CheCko,
    connecting: false
  }),
  getters: {
    account(): () => Promise<Account> {
      return async () => {
        if (!this.publicKey)
          return {
            chain_id: this.chainId,
          }
        return {
          chain_id: this.chainId,
          owner: _Account.formalizeOwner(await dbModel.ownerFromPublicKey(this.publicKey)),
        }
      }
    },
  },
  actions: {},
})
