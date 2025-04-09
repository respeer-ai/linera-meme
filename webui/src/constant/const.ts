const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/9613ecafe7d27cabb2e8114781a76658430d93f4bfe8bdd763dc5b555c91fbb8/applications/45c899e4befdb14fbf753fff96ba3d5fbd73439ce992f0c9568c525549b07b2d',
  'http://api.ams.respeer.ai/api/ams/chains/5b3fa847df878deee69cd8d136bb7b8a76f102ffea876099e9b8294a23d21be9/applications/1fb46cc00addde3190781b0746559728d87e962fa2ef8b02f0a64ec2ef2ebe3c',
  'http://api.linerameme.fun/api/proxy/chains/18d7eb1d560f349b11cd4c84462dfcfbc3fcf85170337ecd18b7e0d82bdbc444/applications/3b20d6c77397bb3df6f7d04b07aa6826287c235611586c6c40652a5cd58e3ce5',
  'http://api.lineraswap.fun/api/swap/chains/df5854178ef7c817fd0107e2f87db0fbd4849188f2e51522933331c84c842c3f/applications/fba84be8e24add92396fcfab0d9552752a9646d887da9fc9aea981e57fa3959f'
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
