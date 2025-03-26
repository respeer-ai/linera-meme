import { defineStore } from 'pinia'
import { dbModel } from 'src/model'
import { Account } from '../account'

export class User {
  static ownerAccount = async () => {
    const user = useUserStore()
    return {
      chainId: user.chainId,
      owner: `User:${await dbModel.ownerFromPublicKey(user.publicKey)}`
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
  getters: {},
  actions: {}
})
