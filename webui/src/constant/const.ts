const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/5af79bc01b4dcddeb4a9fa05bceb9960735d1d893d1e384e7ab276f379a76ab1/applications/2ecaf50396c64f5e3a643090cbd0a3d9f3233fc3c0860a87caece964b4dc81d4',
  'http://api.ams.respeer.ai/api/ams/chains/0545ef9600bc4c40d741baa52228f04db836d74dcab0bbaa1971e0871b2bd593/applications/91585b1cc7f2462de90649dd8dd075c1a11e640eb4616d09b8544febc4c0200f',
  'http://api.linerameme.fun/api/proxy/chains/fa779fdca5e5a871f4f9830ca67952aca0ddda8e407e545ae02e5cb548ead250/applications/45c214b77d62477ebcfcb30c0a8f47173c8866c680a7bfd832b4263facdd20a1',
  'http://api.lineraswap.fun/api/swap/chains/1835c1e46e2cc3cd0ff9821ecce1fc6f9893364241844bddeecf60a9091ef2ea/applications/33fcacf7de56b96a59f00967b91fd6120bd534d76712948d851cc66a74032760'
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
