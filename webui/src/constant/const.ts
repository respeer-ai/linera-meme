const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/ba8d5b7afa68cff41d364e204f28835bc3f177d306226addf997ef52c69a49c0/applications/8376ca1d2481fc901c95e2818ac48820c706add48d48ed7afc41cb8da8663ed5',
  'http://api.ams.respeer.ai/api/ams/chains/39bca2edf5d27eba30ef879a76feb710653f786331682b185084a0e7df79930a/applications/c2d902b583762b4f1af831c3306ccc389d71704da5e097bd6fbd52bd6c9a472a',
  'http://api.linerameme.fun/api/proxy/chains/0e5006934a39ac7f11c9e5833267a7a914baaf9a29da27d49a5725998bc73ca5/applications/5641e063e683101f9b5d954c0c5ab2a4eef908a9fcc92595370d6e054f34bfc5',
  'http://api.lineraswap.fun/api/swap/chains/7669ee209b57a66b9a7f62e7eb2699727b622066f7fe90a074ee9ee0ec585ff3/applications/b413f5f331f8bbb4ab6084dda5c9e966cd75f2920241f4647457b4c139baef97'
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
