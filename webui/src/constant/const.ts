const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/7374465172cf86c0204787a8c3c8b48b1b0a65cfb5343274e2360ca775a3db55/applications/e89e5c6062352debd457e330f195fe8e63851637e758712d4df93f25c8ae0351',
  'http://api.ams.respeer.ai/api/ams/chains/8e417b301d25353c210136780d664227c42a5b15043c333fbe09141e8e6de680/applications/48ffdf3d93b92d23b016a29c69c598fc4d790540d01edf2ad7d79cb4ad253c27',
  'http://api.linerameme.fun/api/proxy/chains/e10f4d35423336b524372337f306659fd3ae8a38b1750869ec74bb55dbb49255/applications/ad49cfafe5182ced11543634ed676dd46e8cc97811375c9fc9f772084652b25d',
  'http://api.lineraswap.fun/api/swap/chains/4930b01b125a3d02fdabd3f1b88a24a9f12827fdad311af53152f805059ad03b/applications/d15858e36a025463225a58ffdb72178da11edcf7e6dc84cccd5cd6d683a301f4'
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
