const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/d710c0480df4f19176258a38e33c6ec7f6c79c31524da3ea518a66811cb75c56/applications/b2b55fdb5b65bd5bed03e6b0edcad71758c0be10ecf2adc13eaef9a35d4d1b50',
  'http://api.ams.respeer.ai/api/ams/chains/2b1be50934a137c6dc5c1dd65c98c24864b37a2e5fee6e871897f3f84616417e/applications/311f8a403dc7ebe975d188e483cf8c2aaa69f1f229c2f020df18657c78a60699',
  'http://api.linerameme.fun/api/proxy/chains/481f21ce0274d0435524c7304b66cbefd41d78b7712e47b91d668ae924a53aac/applications/9e8527311fcbe815e57b71e9eb7faf0e8a5a4561a2b1dc2332059595f894b8cd',
  'http://api.lineraswap.fun/api/swap/chains/8fbded953c66b9954331e33ecf606b9e2871eb15a53ef2df6713771a62069232/applications/ec814a814dff31023858d632690a21313de554d21744f6504ec060c49110cb9a'
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
