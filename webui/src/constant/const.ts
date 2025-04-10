const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/0c63144d9b9dc24ba73a42800bd4b55f4d884440e1efcc7d521c14e2d7e2bfd4/applications/38a07cf2c521619ee7728bc7b8cc4925e1295aa05fa5b9d881d4c18b1cb80c62',
  'http://api.ams.respeer.ai/api/ams/chains/70aabf89a72a79bf07e2dbae0aa791716c6f4a6461f5e66695c12cee313e0187/applications/a8ab4fe6a0bd7412ffbd7936ecfb0887118259e21caa4f7c44550e0f5d134921',
  'http://api.linerameme.fun/api/proxy/chains/cb6d25ab3c49a708015124ef92d7db3636c4f459f9e929bd330dcc0de320614e/applications/8a8d4f92a8579ae18b417846de3cffbca7115435ad34603f76438db7176ebaa6',
  'http://api.lineraswap.fun/api/swap/chains/45c992bfca14a795de7d3d9aecb5c9a91469d113e984e9c270c9841b6404bf59/applications/90c7a2cd705acd52ec0b6013227a80ee312bd621f0d8efc16f9f90894ba17ff0'
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
