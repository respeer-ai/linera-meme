const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/8c45f8183fe0a00cbca33d54c2e08b62ff1dd34cc7044f32d953458f2d87591a/applications/d9557e7f8171f4ea47ba80519a6f8dfc2875e162977d9c184b50d00458ec9651',
  'http://api.ams.respeer.ai/api/ams/chains/28b479a3dffeaa7248db91c36362953bd0f72add6a59b76f19aa97cb68f09778/applications/33e85342bdfd433c310f1c5a81dc877dc01064a7c424deaf82394ca309eff4e2',
  'http://api.linerameme.fun/api/proxy/chains/bdcbc659fbf8c16e6bb81f34f9b8ac02f4c92ca83467b9690193fb6f1608c8f4/applications/ee15f1e17769c630bd6f30804441beabf92449a844b80d6686e58fae9612a868',
  'http://api.lineraswap.fun/api/swap/chains/aca153521c9a1dbd3930d24dd219a7c49753d83729aae711cadb9d1a48e5fd2a/applications/49229e970c553f5cc269f0169b839a7d27ea5959bc9962d307d6219abaa6eb19'
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

export const LINEAR_TICKER = 'TLINERA'
