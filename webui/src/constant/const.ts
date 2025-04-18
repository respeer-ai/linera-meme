export const formalizeSchema = (url: string) => {
  url = url.replace(
    'http://',
    process.env.NODE_ENV === 'production' ? 'https://' : 'http://'
  )
  url = url.replace(
    'ws://',
    process.env.NODE_ENV === 'production' ? 'wss://' : 'ws://'
  )
  return url
}

const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/d49a79859385c2e55186074c761e6fcb3906222e300cb9df0145d3bbd381809a/applications/bb401dc5d6ff76c4f3b189aaf7972050d0d04196dc0c03310f2b32aa16b6736f',
  'http://api.ams.respeer.ai/api/ams/chains/f10dd7dc4e903a4095ee3976ccb425589fc1cf7c835f2ed8291480001d9489a5/applications/9a889af431f9739b947abdfd6effd4dbd0daeca92ad428759b51149c9ce84437',
  'http://api.linerameme.fun/api/proxy/chains/085f7b2a001f0591e1eccf83230f61c12ff3a9dc0cb7f0b69b94a6ed0213ce70/applications/5d16f56958bc4501f5f6c4c90c06c3a783edc7bc872d72cb79a12dc32b8b5ed3',
  'http://api.lineraswap.fun/api/swap/chains/f4bcf8d9f20277cf309b00d3ef1c449a6d982416aa1051610c2b7289d4a66030/applications/03c16953c2cbea1b0f181604b116d648c6bd93db8dbd404f2bc7302c4a70c583',
  'http://api.rpc.respeer.ai/api/rpc',
  'ws://api.rpc.respeer.ai/ws',
  'http://api.kline.lineraswap.fun/api/kline',
  'ws://api.kline.lineraswap.fun/api/kline/ws',
  'http://api.lineraswap.fun/api/swap',
  'http://api.linerameme.fun/api/proxy'
]

export const APPLICATION_URLS = {
  BLOB_GATEWAY: formalizeSchema(URLS[0]),
  AMS: formalizeSchema(URLS[1]),
  PROXY: formalizeSchema(URLS[2]),
  SWAP: formalizeSchema(URLS[3])
}

export const RPC_URL = formalizeSchema(URLS[4])
export const RPC_WS_URL = formalizeSchema(URLS[5])
export const KLINE_HTTP_URL = formalizeSchema(URLS[6])
export const KLINE_WS_URL = formalizeSchema(URLS[7])

export const SWAP_HOST = URLS[8]
export const PROXY_HOST = URLS[9]

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

