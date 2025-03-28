const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/f332e8df6107b2f5c4ea621de3f8fa0cc208b580857948a45dba86067aecd091/applications/f13d77795fdea16350a6ff40c95549dea75669fe250500d837d485818a5a683f',
  'http://api.ams.respeer.ai/api/ams/chains/2d83879905fa2e06fb41f6f316e1390c001d7d45cc6ae25a0ea8541c58cf6da2/applications/de83d4eee7e3779047736b89d06c04eb8b01be8f41fe234edc5c7cc83d621075',
  'http://api.linerameme.fun/api/proxy/chains/0a8746b77f150f223397363a5bf9751efddb23dcf71d5b1bc8454f790171c5a3/applications/adf42636e2e8e8090b4defedc7b12c840681026a43e0efaf394e9f62c137e396',
  'http://api.lineraswap.fun/api/swap/chains/ab61daf827071b8cfc901c49a2d8201b91aff2cd36cad469ef3b7dd15ec79ac3/applications/06e9e17a44a1423b76279ea1ed3544b078ab5d39d03a2f4f77ecfb5e4301dd72'
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
