import { defineStore } from 'pinia'

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
