const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/7c0b97af9940680989c2b460cc987122e6bc100862166dcd1f3b42b0b6424e91/applications/72414de02400dcf41942377b1d20bbadc53fb93e8179a313f91aefd3a5d0ae59',
  'http://api.ams.respeer.ai/api/ams/chains/a67d527857f7f256a64da96b713dca97a42d949f211e0caf0485976da8674d9e/applications/422379439409e0837fceb2acaf32c35ca269d23ed790a73153c7d9b1a596e414',
  'http://api.linerameme.fun/api/proxy/chains/027d1848b86819c03d7a52123e814ac995cb744184f45aebbdd8730525743d8e/applications/43a8af644db1febadd70efe660a52e3a90e388401c2092e66d93e5b358203f0f',
  'http://api.lineraswap.fun/api/swap/chains/7ba58c9edfdfb3b9a481eb89156cd77247be033d631e86d2f21a2723199aa495/applications/5432bf8289dbf774a03b73dcc9cd7d7c8f6d5ede8a7fe50f8aa3ab40cd543c2a'
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
