const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/24812d0085777df9f19cf5865e14b1473bc4d05fc16364705747ab0de1a5de5a/applications/717328107fb71afddec17bf35d00a0baebfd9c051ab4b4bb6b6ebfa6a185c0a3',
  'http://api.ams.respeer.ai/api/ams/chains/527e489c816e06eaf03fa9b257a7f5a356f7160c19cde0511c840a0ad2eb5073/applications/8532efe284d72fcc0433b8102afe2e879df76f411c59cda12fed806e353bb33b',
  'http://api.linerameme.fun/api/proxy/chains/ea5a7fbdda84af50d6509a582c0fdd81305c15538d5aee33cfeb89bc7d1f3794/applications/d81f0be077beec124195b7c40c3a4171dfc84eff909f9988b489d398cc165631',
  'http://api.lineraswap.fun/api/swap/chains/5e89b886b5a7f45b605a295271eb26e8ecdd267995f9137bc391c232b51ec5db/applications/6e568d9c511c407c4f2f0963f8f15032d2f7947dbc5e567709070a633b359847'
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
