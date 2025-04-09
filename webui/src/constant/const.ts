const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/7aa193efefa274169777651a784cea1260ec4973efdee8747da5081cadf836ae/applications/85869c9050d14f1708f4c2b7ebf4bd082bb443ae84f749fdb58e9d999283b2b7',
  'http://api.ams.respeer.ai/api/ams/chains/d37eba47e2098cf3a776616eb524bb89b5dcb11b173119e7d3c156a60ccff18d/applications/f7415bc5f420cd6649400588b00dd962f3aaa74699f4a6953ce64a21ecf7e77e',
  'http://api.linerameme.fun/api/proxy/chains/dc15445f3926dbe7d56f748262a2565aec538081935c6fb7fddbb6532f7d8b05/applications/c5e24c8d33da0453b55bd9b602a7bb1a60f83e61d8dca885297b0744d39385b8',
  'http://api.lineraswap.fun/api/swap/chains/d47b442ebf70d28c60acc3207cfdf58713ac7708f58bea024d2137751e203123/applications/391579743bfda6d22d94cc8f02291ffb40fdf87f8ea88f38c61bbe8a438a1ac7'
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
