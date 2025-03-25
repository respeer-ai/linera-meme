const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/19f19c17072df551d9b800a95e84d257a923b7fe24027fbd74bc07495900145b/applications/a4cda42645b757b2450a2603bd8372c1e0cdc5cfa89deb3709a1853c96341d0a',
  'http://api.ams.respeer.ai/api/ams/chains/7f004722274de5c0ca6d8c9809f10223ee569d1b0146b293c2ed369cf6adabea/applications/2c37f8b8a968c984be315efc51d493a900edf146d5a095f7ad8232a811ecbba2',
  'http://api.linerameme.fun/api/proxy/chains/577e6665d500bfa4098c58c57f09c0d821263f7d8236fd72f544fd1654e2e581/applications/da5ba1e9c7d911e59f3533b96b2714aefde5011ed2039ede94e602cab9f152e6',
  'http://api.lineraswap.fun/api/swap/chains/6c348fbdc30f52f208557d2a8930dfe45abdbe653c338582bf596d0fadfcc425/applications/fc409c822ea48a3f6f4b88a4ea20b18e0e22f83468fabae51b88435e7aaa6464'
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
  return url.split('/')[-1]
}
