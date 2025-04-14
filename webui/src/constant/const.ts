const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/45811ab196f3515d49e38d8e258003c11da7058c3c78a513fd324c2275350f22/applications/14e4d594c21add305d6aaeedf20a55a90842137a2cc0227e4a7099aeafe99d8c',
  'http://api.ams.respeer.ai/api/ams/chains/8d74eaf1077afa6b567a6e63efa08002fd143811f30dda54ef8ea288aac9e646/applications/1729be59dfb5520cdbcb7dc49fa9fc5174ab7168afb34da9e35b74b6fd3b309c',
  'http://api.linerameme.fun/api/proxy/chains/d22bb92bc27c92a4aa85c7e8874aa9164f1e328e4118fd66132081fd27f8f29f/applications/159da5af6696c7f460a0684eb2c78cca28b6d2dc7c3322a2440ec452859996f0',
  'http://api.lineraswap.fun/api/swap/chains/da9482a95a40b0c48494e37b56032e4403c2f4c1f02b1f69fb95fe4fb939f103/applications/67bc77796692f0e8284d441f54446f191ec7687cf09f06eba970440ae1bafcac'
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
    process.env.NODE_ENV === 'production' ? 'http://' : 'http://'
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
