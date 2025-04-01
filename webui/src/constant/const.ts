const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/14cf2a2374301748971af919b64ebd445be2134aba3af583700f70eaf5f8f49a/applications/db65e2db087062e87ef7f2331acac40889f613759c495c6e3ef720bf0ad52d8a',
  'http://api.ams.respeer.ai/api/ams/chains/0a0356a40266a9fcd238b3f993b8c393eb8757b4b60b5c8ce6deec663a94e535/applications/1d69bfa7738b9c48de1a7c293926ad555c4aec1cdae796b5e06dc6f540f0550b',
  'http://api.linerameme.fun/api/proxy/chains/36754f4243adca96cd21a1df65116a8183bc5cf5b7fea4e59b0fd3cb78561ded/applications/73b1dde0327a37c724777bdb75a81aba7abe355db22a1488c781bb88103ddd0c',
  'http://api.lineraswap.fun/api/swap/chains/b9f2146bce2e190c946c3adb63e282ae46f6eaed9975a47e9af1ea3c31ba40da/applications/914fdf5d9bf72d2fea80df4ce0e6f132db44a6d32b060c2235ce252c12ea60a9'
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
