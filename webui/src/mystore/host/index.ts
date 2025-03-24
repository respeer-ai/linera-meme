import { defineStore } from 'pinia'

export const useHostStore = defineStore('hosts', {
  state: () => ({
    useDomainApi: process.env.NODE_ENV === 'production',
    apiSchema: process.env.NODE_ENV === 'production' ? 'https' : 'http',

    amsDomainApiHost: 'testnet-archimedes.respeer.ai/api/ams',
    klineDomainApiHost: 'testnet-archimedes.lineraswap.fun/api/kline',
    blobGatewayDomainApiHost: 'testnet-archimedes.blobgateway.com/api/blobs',
    swapDomainApiHost: 'testnet-archimedes.lineraswap.fun/api/swap',

    windowHost: 'localhost:8080',

    amsDebugApiHost: '/api/ams',
    klineDebugApiHost: '/api/kline',
    blobGatewayDebugApiHost: '/api/blobs',
    swapDebugApiHost: '/api/swap',

    erc20BytecodeId: '716c598da8db64bd276d6efbae5c67842c9caf16eade6587d51b0ff001e4a7b407b5e65376146b60763dfc1776a4353e15e3333f7ba53ccc88756f2b0d6308d2',
    swapCreationChainId: '3414591cbf66cd0ed4f46dd33dc88c5ce296204d164f31a8c0a953ef6826afa3',
    swapCreationOwner: '6bc164559c93794ba15cdb803d167370f49abf7920ca06f5e148264020fc7c56',
    swapApplicationId: 'ca30b7409bfa4a373c2597ca63568ce698679c53ddeef9cc033aba955d2823b5f332095b5e2bb1757c03fd11fa58e930c7f6e28cc5cea0309f21db1dca210a223414591cbf66cd0ed4f46dd33dc88c5ce296204d164f31a8c0a953ef6826afa3060000000000000000000000',
    wlineraApplicationId: '716c598da8db64bd276d6efbae5c67842c9caf16eade6587d51b0ff001e4a7b407b5e65376146b60763dfc1776a4353e15e3333f7ba53ccc88756f2b0d6308d212b556b01f0245ba591b7030641eb0743e492e3e372d79b476d3b3364b2985ce060000000000000000000000',
    amsCreationChainId: 'd6d88c37dd1cfaa583d33528218c0440ab13b99d62f794f482b0c03cc55ba6bf',
    amsApplicationId: '61afe169cf65c3798ebe9f968f0317bfb37a1087a131efa180308ba3d82e8ba53f73938f84203fb4f8cbc8f0a0eab6101872be430b536c756d5bfa7855d2a868d6d88c37dd1cfaa583d33528218c0440ab13b99d62f794f482b0c03cc55ba6bf030000000000000000000000',
    blobGatewayCreationChainId: '20d5c508d74303f31ae4c63f211994ac0b34af03daa0bfc5eb281f01b0916415',
    blobGatewayApplicationId: 'a3a8b9a812d788136e445729d864d3ad19f58c718934a08bb82058a0c60d6b0b6badd4e18327a0cb07fbcb3d1340b754ad0b1e9a8ea5fb21f85b5a45d7bd4edc20d5c508d74303f31ae4c63f211994ac0b34af03daa0bfc5eb281f01b09164150f0000000000000000000000'
  }),
  getters: {
    formalizeAmsPath (): (path: string) => string {
      return (path: string) => {
        if (path.startsWith('/')) path = path.substring(1)
        return this.apiSchema + '://' + (this.useDomainApi ? this.amsDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/ams') : this.amsDebugApiHost) + '/' + path
      }
    },
    formalizeKlinePath (): (path: string) => string {
      return (path: string) => {
        if (path.startsWith('/')) path = path.substring(1)
        return this.apiSchema + '://' + (this.useDomainApi ? this.klineDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/kline') : this.klineDebugApiHost) + '/' + path
      }
    },
    formalizeBlobGatewayPath (): (path: string) => string {
      return (path: string) => {
        if (path.startsWith('/')) path = path.substring(1)
        return this.apiSchema + '://' + (this.useDomainApi ? this.blobGatewayDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/blobs') : this.blobGatewayDebugApiHost) + '/' + path
      }
    },
    formalizeSwapPath (): (path: string) => string {
      return (path: string) => {
        if (path.startsWith('/')) path = path.substring(1)
        return this.apiSchema + '://' + (this.useDomainApi ? this.swapDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/swap') : this.swapDebugApiHost) + '/' + path
      }
    },
    _amsEndpoint (): () => string {
      return () => {
        return this.apiSchema + '://' + (this.useDomainApi ? this.amsDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/ams') : this.amsDebugApiHost)
      }
    },
    _swapEndpoint (): () => string {
      return () => {
        return this.apiSchema + '://' + (this.useDomainApi ? this.swapDomainApiHost : process.env.NODE_ENV === 'development' ? (this.windowHost + '/api/swap') : this.swapDebugApiHost)
      }
    },
    blobGatewayApplicationPath (): () => string {
      return () => {
        return this.formalizeBlobGatewayPath(`/chains/${this.blobGatewayCreationChainId}/applications/${this.blobGatewayApplicationId}`)
      }
    },
    blobDataPath (): (storeType: string, blobHash: string) => string {
      return (storeType: string, blobHash: string) => {
        if (storeType === 'S3') {
          return `http://minio.respeer.ai/api/file/v1/images/${blobHash}`
        }
        return this.blobGatewayApplicationPath() + `/images/${blobHash}`
      }
    },
    swapApplicationTokenPath (): (tokenApplicationId: string) => string {
      return (tokenApplicationId: string) => {
        return this.formalizeSwapPath(`/chains/${this.swapCreationChainId}/applications/${tokenApplicationId}`)
      }
    },
    swapApplicationPath (): () => string {
      return () => {
        return this.formalizeSwapPath(`/chains/${this.swapCreationChainId}/applications/${this.swapApplicationId}`)
      }
    }
  },
  actions: {}
})
