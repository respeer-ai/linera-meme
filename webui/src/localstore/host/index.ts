import { defineStore } from 'pinia'

export const useHostStore = defineStore('hosts', {
  state: () => ({
    schema: process.env.NODE_ENV === 'production' ? 'https://' : 'http://',

    blobGatewayUrl: 'http://api.blobgateway.com/api/blobs/chains/d37eba47e2098cf3a776616eb524bb89b5dcb11b173119e7d3c156a60ccff18d/applications/1d5a10ac4847e8e33f9d9bf48f5e40cfbbdd3dfd932175fce2c90313f58a8b2d',
    amsUrl: 'http://api.ams.respeer.ai/api/ams/chains/042eaa8162f43e4dcf5346603e86016ee719d224f9f1df37fbfd70fb6cb70d7a/applications/bd5f3b4246e504ebc01c1f8ea0f964d1c114bbde4b00a29c3bc6949bf652aecc',
    proxyUrl: 'http://api.linerameme.fun/api/proxy/chains/8994c94fb94a84d59f31280923b70cf8bca320a46c6af8f96529f0a837d1f9a1/applications/edcb213fe61101e92e640937a416797846ab9db232887af8a8b946011e0d9515',
    swapUrl: 'http://api.lineraswap.fun/api/swap/chains/dc15445f3926dbe7d56f748262a2565aec538081935c6fb7fddbb6532f7d8b05/applications/3865c36ceac24d06196383f3645cc6091f34724f91988fb31d060f25cfd6f11a'
  }),
  getters: {
    formalizeSchema (): (url: string) => string {
      return (url: string) => {
        return url.replace('http://', this.schema)
      }
    },
    blobGatewayUrl (): string {
      return this.formalizeSchema(this.blobGatewayUrl)
    },
    amsUrl (): string {
      return this.formalizeSchema(this.amsUrl)
    },
    proxyUrl (): string {
      return this.formalizeSchema(this.proxyUrl)
    },
    swapUrl (): string {
      return this.formalizeSchema(this.swapUrl)
    }
  },
  actions: {}
})
