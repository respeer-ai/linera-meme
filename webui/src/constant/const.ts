const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/17940d83d49fc7ce5f14b36f676f493e6eec8ae34e1781717ba60ffdc66c9390/applications/244459b40e42ba90f75fc561b4ff4b0687ca5b2b6a08cfd4b70806c4e54b7cd9',
  'http://api.ams.respeer.ai/api/ams/chains/4a44f6c64c06824455539ee223955520e08a831a388287871e4eceec081d7c13/applications/b52653e5e8d6c169eac74cad4f2881e6ae6757e23966f791fb7897efd4adbdbb',
  'http://api.linerameme.fun/api/proxy/chains/3e077ac807163e523661532d7a9f6b51214b5b876fb081429d1fac2659667fa2/applications/df6f9aecb6bb0d8355f274d2bac6a418338deac231c895ba78fd1c8b2dc00331',
  'http://api.lineraswap.fun/api/swap/chains/6581f56d52f0e271151d7a0d4939963cee5391f4bdb352722d336cf2b9b42460/applications/873afd757a3a602e5b477c74309f9502d85804af5aae609b63c3334b1e8f3fc3'
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
