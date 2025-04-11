const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/48beacfb0896786049bf4f86025dfba402cf7795de70c7b85052eae4dfccfef3/applications/c1fd64bf64a9a1ccc399a50ee12446d8b566b9989f2593b79f42cccc41098746',
  'http://api.ams.respeer.ai/api/ams/chains/3a4e2bf06672bb56e3e3ecc51d0c241ad9c163bd00abaf64fc2ffbe13ce34106/applications/ba02f8c9589712acac258f7bd6f52c4ec46012c9295381dff5fe3c5681dae9e9',
  'http://api.linerameme.fun/api/proxy/chains/8484f63cad90df95965d80d277cbade1a8983c6e890ff242abe3407d4fdb629d/applications/0e7c5400aae71f39d35f60095580d029b890e823dafa1fff8dbdf7521e512404',
  'http://api.lineraswap.fun/api/swap/chains/f993d1e527808c70498d52e932a7dadc485e286bb73ae9e87ccec92f2e441cca/applications/21917f8effc086d69bf9597247aa5c3e72174274fabd7fb4ddbf836c6962599b'
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
