const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/67d885a8a7d96be7a36d0de4e1a2f0629526fe0a64773bbe357da2bf076ff74a/applications/dad4dc3cc21a33daffa4ac6e3f5af2b3063fb338eefbb193abc3ef7d462fb432',
  'http://api.ams.respeer.ai/api/ams/chains/287400fe928f6f40924ce6fa7a8b1f5a223070366a4b200ed390a105708a89d8/applications/e292b0362f91857db19964c11fd410cf647dc23a6ef81b5b6bcece4700bc92e7',
  'http://api.linerameme.fun/api/proxy/chains/2b83d762dfcde070a6f9d622b924f05592e8506d9e3bd9e3f46b824ff7cefbe9/applications/c43857ddb35571cfa28fa83fce49b97f06c5537761668b0ada4417da4890841d',
  'http://api.lineraswap.fun/api/swap/chains/b2d70d5ebc09162cee815f985744dd534b0668f668afe076f4ae22b9f3a9f0b6/applications/26e8cfc9c900c7c76dc61aa74b9634060ee8a939ee97deebfb6612de08667f49'
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

export const LINERA_TICKER = 'TLINERA'
export const LINERA_NATIVE_ID = LINERA_TICKER
export const LINERA_LOGO =
  'https://avatars.githubusercontent.com/u/107513858?s=48&v=4'
