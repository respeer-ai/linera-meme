const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/3700f024be40ad002ec4429684fbd7b9057c71e46e35d513363e3ea2620e80e1/applications/70a6445b2b7cbeef3ced7105d4085dbc9b420daf0314793593b5d99b0796bd7e',
  'http://api.ams.respeer.ai/api/ams/chains/ac3bcb5e44441f5f651db9f87235fbba4cce37ed205a9129cba20463abba4b61/applications/53bf2a8563233e0fc836a27b6bda9d12621db82a5cc4bbfeee89e30311eb4c3c',
  'http://api.linerameme.fun/api/proxy/chains/37dbc3ce32773af3a39e9e0c86dbbc5126111b14c9ba481bdc5d15f2fcd4074b/applications/142beb332aa37f610717611a2634530a26b2cbd4d017b2dff31d5fd872696d75',
  'http://api.lineraswap.fun/api/swap/chains/7533707b1ab32d0c5867ac72fee37609c983fe1ce4aa67b872fc83745f09efdd/applications/b4c6dd17cf6a87c4e27e5c629d489c1bda113b2a3c7ac140723cd00375e392ab'
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
