const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/d7697687e78f3f6e382933a9f6dbe9168958138149a0ae954c2156d5130ac6c6/applications/6481eff0d743aa5d9275e49bbd6134990c897425ece84ce4e356d5744cd8266b',
  'http://api.ams.respeer.ai/api/ams/chains/e9270af2ab38671d766df19ab0bd528cee0c79d899661655ac0c272035d114ce/applications/5c65446720b3bfcef5d35264b200976f5bc4d620063118716137a16268e4e307',
  'http://api.linerameme.fun/api/proxy/chains/a6d56261887281d083d22e445269f19dd10517b01b783a90b55105d8edff290c/applications/c5509fc4bdece1ce37b89d56b5b43b0dc5a67bfbf970260784cf9d1649c7290e',
  'http://api.lineraswap.fun/api/swap/chains/f21f090be39e7e77db329c26d22012be6b17661fe31d70368208e654b917d087/applications/942ed97b701c6f681091c192ae1ff7a3e50db7e02e85989618c632c21567149c'
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
