const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/0f01f62e5a1d1764baa378d7c115973b364a7474ca8dec5bede43016ccb48a73/applications/beed592e9cc02efc23948cee83b24aaa51e5ff45a89517306ae3e23f14976f20',
  'http://api.ams.respeer.ai/api/ams/chains/3b5a5a6790579fca8a6eeea71c2de75252d1ef3b9747a765589907ae28ad895b/applications/4f705b6d9a8a0d25e7f5693b80161dcd7513bd09ea35f51db1aaae7596a5cdd2',
  'http://api.linerameme.fun/api/proxy/chains/139c9440d3dfbe34b39dcc19beb286d3ea031f699d96bfda5926341be7e8d502/applications/0b8e5dfb61c656424c41b153663d271ce201188bc7ef838f34233ed7810eaabd',
  'http://api.lineraswap.fun/api/swap/chains/943a7f972e5dd64e126c8a22e69e8d1e492cd398b730db6ab46e780fe4f05c2a/applications/c2477f4f358f0cdb5ce370a3af07698c97ea135f8d4f6538aa434f96be912cfc'
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
