const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/79813b1aa3b80a098c4cd024636beb3fb97d964df807e22878c171b7cae4d674/applications/51f9be19af6208923308a10b1cf1b6b97ffcbd26eb618b85b9ff1d33afcb2745',
  'http://api.ams.respeer.ai/api/ams/chains/e04c1924add01383c965dc863dcd15eee298931609a5f0e025cd4e8281765f4b/applications/5dba5dbe1a7d4f1867b0836da430845e80ef003161c8401b9077803979f3c7e2',
  'http://api.linerameme.fun/api/proxy/chains/13bbc875be6068a104cf9fac4df009e93c4ec54e6b0a6053dc1f71f4a0152e12/applications/0a5f42f6fad2b1ec80d73e30c3ad76c946c07fb6e464bc73c96d815b51eb73ab',
  'http://api.lineraswap.fun/api/swap/chains/1bcee38559b5bc5b803777760f0b825f57782eb88102de85bd47f12e4994158c/applications/c389351e798aa2435e7d43e75b3403ebd08efe921f28c72dd365f1172a2ebd13'
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
