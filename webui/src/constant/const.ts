const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/2121221068c16d21ec9baa00393463ff50e296500a69b0fec4b53484cd14070a/applications/e2a334b553320a3dc408f127dbe3e43d944e25cfee182aa17561b2b012b026d3',
  'http://api.ams.respeer.ai/api/ams/chains/67f064a51c7993f44b8d5425bceae16bec1d52190e0ff44e026e31eb72e8dc2d/applications/a6c4946b1b98bee361345be0506087867bf7f5e4f672c942828752f97b35e0a1',
  'http://api.linerameme.fun/api/proxy/chains/5cad844e0ea085c620b2d7742bc7fde7d47d64ef3791b836d1d79f111870c2d0/applications/e64e71bf688cfd86b0883de32cac88aa216bd1b2344c0537b5aa440b36e80971',
  'http://api.lineraswap.fun/api/swap/chains/4026fd1bf21dcaa7d8b98a51100d60b2b3e9565269180716885a713965479afd/applications/b2eab58979ee404f5528eb27f7d848de5201f2d5492115f01b3e3b961355bca6'
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
