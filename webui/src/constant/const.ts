const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/8d784407f3375627d47e8962558022fad7f57b409d99c736776fbc0a8cfc3a63/applications/d9a736b718e89f469496d5c0b90490090e60891439ae613eb3ca491f66a2852b',
  'http://api.ams.respeer.ai/api/ams/chains/d22c7aca1b4ab01b9a5f401aebc8bb53e4d518ad47cc2d0f88d1331733f22603/applications/6cfe709c5803931d613730bc3c2f0b09d9efd4445b9d70929b7a70e420e78bd1',
  'http://api.linerameme.fun/api/proxy/chains/b6880a33ec8de02b70b91209bbc61d84fd60a38360474b8735e0fc257f26b9bf/applications/9422b4e8d2b36dca5dfabbbcf55b7841d0455b9ac9f5bebfd56bec50a4d4fc22',
  'http://api.lineraswap.fun/api/swap/chains/1d2e5cb5b295b559e6bf3a3eba84823d4cba8f2e20ff7d28ef0327f4cbb4e02a/applications/aa9edcadcdf5ec3fd544b317a717901b0dd30bf8caa0837834e6392f7b0296c7'
]

export const APPLICATION_URLS = {
  BLOB_GATEWAY: URLS[0],
  AMS: URLS[1],
  PROXY: URLS[2],
  SWAP: URLS[3]
}

export const RPC_URL = 'http://api.rpc.respeer.ai/api/rpc'
export const RPC_WS_URL = 'ws://api.rpc.respeer.ai/ws'

export const formalizeSchema = (url: string) => {
  return url.replace(
    'http://',
    process.env.NODE_ENV === 'production' ? 'https://' : 'http://'
  )
}

export const applicationId = (url: string) => {
  return url.split('/').at(-1)
}

export const chainId = (url: string) => {
  return url.split('/').at(-3)
}

export const LINERA_TICKER = 'TLINERA'
export const LINERA_NATIVE_ID = LINERA_TICKER
export const LINERA_LOGO =
  'https://avatars.githubusercontent.com/u/107513858?s=48&v=4'

export const KLINE_WS_URL = 'ws://api.kline.lineraswap.fun/api/kline/ws'
export const KLINE_HTTP_URL = 'http://api.kline.lineraswap.fun/api/kline'
