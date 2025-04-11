const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/c443896546320204203449c7b69ddfcba3395079bfce39e78f9f809cf849e5e5/applications/8a1a3445f71d36df39cd71bfddb306722960497c7cde2171a8382e6a4aa87f05',
  'http://api.ams.respeer.ai/api/ams/chains/ce1b68f09ca72c3df6849d063129dfa1002800080235fcaf490f3e9ec0787937/applications/6a4966428fd61be6f9918de76df9597e0b17cd5633c0ab6bbfba9f2a379ab67a',
  'http://api.linerameme.fun/api/proxy/chains/f289164f7845d862fef199cc83e774a95468c52d32a713c67bf83bbb643033c0/applications/927ef57694d9c589c070748bf0f26ace95c47962404feb4da91a8ceef8b1e4b7',
  'http://api.lineraswap.fun/api/swap/chains/bc719df5ace10640e457d00ff9dca92ffd1b862c7c955da0d0b8306dcd0547f0/applications/94e9fdeeecdc89dcb9dc2586ecda158acd1306a4154f7d10476abcf57ad45b0d'
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
