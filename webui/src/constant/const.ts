const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/b0b6180089c7c2ac24ae16b9e14d6ad86b7b5d2d5a2a7551ff5bddd59622144f/applications/1ca1dd569f6d22d72adbad3f072a3943504e370b1a66d15699d38b9ed1260412',
  'http://api.ams.respeer.ai/api/ams/chains/0a86b991a7ba46db59682385628d4387df142a9f34886a7508a415a93905dc6f/applications/feaac78324b11f975c55a177c960f63da488b73d24eef9cb61e217f79be386f6',
  'http://api.linerameme.fun/api/proxy/chains/7f370809a6374885f4ffe2f21ac4a35462e74ffa0b6c586a5eb179bfecd0aecc/applications/56e69166b827bd41fba6f80867f3bf9c0348b1c9bcd06c0fa6c5de55d25bd478',
  'http://api.lineraswap.fun/api/swap/chains/223a84853518ce414f1d32084f04e79f61bb88ccb2d03a9c30f3f611b2a95a49/applications/972a1e04a1cae73d9298675802c413ba2c7b645840f4a1806b4c58a537aaa27e'
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
