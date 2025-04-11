const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/368ebdeea0af47ed8b527f7a05c75c6962c93cb29f0942b60d301314777e5a14/applications/8c00314584577daab013ab15b6b249a350661017e2c414c62f8df8b39f18ce24',
  'http://api.ams.respeer.ai/api/ams/chains/2203469f664dfa44f8905c311e891b2670d2b8f08a47821ee95fe328bab7cb4a/applications/7a5d5378eb04eb6210cab0bb4d6a82772ca8453ae593c477b426b815796ec596',
  'http://api.linerameme.fun/api/proxy/chains/44999ac7b4a2f04b455c3e8d7ffb0fd2539f960eb4bd5a5db3aa7055e1624c82/applications/623c17c8a1f5f7ffd90486570d6eaa790afe98bfbcd6958c5a16fd550063cd59',
  'http://api.lineraswap.fun/api/swap/chains/088039150ea9da8d65f86d4bae80bc7678632e06cacf4ae981a3ff7461c54f09/applications/6c9394d8e64e4cbce485657303dd53dec3a14fe8a09da0813a8c6456569ccc68'
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
