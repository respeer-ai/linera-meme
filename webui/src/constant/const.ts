const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/5f3fd062c5052fdd620ce44be0f1f2b1d4096bf7a156e1435a76d11b397ffd20/applications/053a7b87eb5e433a13a37bb8f112016c2f8d0fc636c59a32f97cc8ddc89b6d53',
  'http://api.ams.respeer.ai/api/ams/chains/705de9d8549e645b68a683d76c410d63cc381cd2a7c2588c6dee5c1ca2ca0660/applications/f3204a331ec19171f1f1e4bc5c73a26dde98ad5993c9a83d8e54e66b4f82f7ea',
  'http://api.linerameme.fun/api/proxy/chains/0af3da2ab47d1a711e52efe69c98106b3cc20ffc9ae1c774db0000a5d9bdcb13/applications/8d2da439b0aef4b142f0a23c11110aa193894386a0617365453f0d3a8ddd81c6',
  'http://api.lineraswap.fun/api/swap/chains/00407707aaa7ba130cb748d4971af9555bc35588bcce1aa8e4e6fafa697824f8/applications/721a277d499441309f4de41eeab0dd3568f7aadb5ea9a9de4418552dfc2cfa91'
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
