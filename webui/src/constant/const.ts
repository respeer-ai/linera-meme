const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/3a7fdc3784c827746f91aad34769f19b2afb3012d3b0be572c79f82e986392d5/applications/f8fea29c86c9bc49daeab898f8a2082fef762a9e3ce5ab897ba93d7a768ea847',
  'http://api.ams.respeer.ai/api/ams/chains/ae777edf58eef412ef6e126f61305eca47ae1b625c644d3cbd4f592e4c185a04/applications/c799eb0d6a0bf51301e898ca4033e3c2ecca1d37179dfb3fe2e38d08786a7ec2',
  'http://api.linerameme.fun/api/proxy/chains/ee78d6aa772b8b7ee075d0323b332fbab640101e8746c1bcb09395da5692908e/applications/e1fb8b3805ddc004ab79944e1bb1827567d6df3742b78e7f804880a69a46b79a',
  'http://api.lineraswap.fun/api/swap/chains/2ce593947de45213ee4337ad93a4916595f04afacffff37dea35667f74c50008/applications/797a105ee3c5bdf1de1a0fed466ac4a777b8c19146072495b811fee38d582d7d'
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
