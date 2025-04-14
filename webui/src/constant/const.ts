const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/c23f52372ec8831e46ff20327be603c527317d0ac07d66a13cade205666f0bc3/applications/039649061ebad00066dc3c693fbb3aaaf7965cfae17406d9b7783d84bd231363',
  'http://api.ams.respeer.ai/api/ams/chains/3e9f5ba2e445f33e08cba5470db2c736a04a48cca4facb8775b0b75a04e2ee31/applications/d6a78932d9e052705ec7ae83ed420c907e0ec0471105715c30bce0956c1da550',
  'http://api.linerameme.fun/api/proxy/chains/703f9244acca94651fa4cb504f36345e51e65475681d5642121bb4832748a570/applications/2ac7e1989749f10769da17cad8c549fca9287f367ff0d3c84f36e5e76319ec0b',
  'http://api.lineraswap.fun/api/swap/chains/704c16ac850d49f6f6cab1cf87198033daeede3797e25949f55ba526defd2a9b/applications/d9d85627780f66cf7c040a42d16eae1101e471ce7b30c2fe6b6c88be5845ea2a'
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
