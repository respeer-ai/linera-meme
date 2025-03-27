const URLS = [
  'http://api.blobgateway.com/api/blobs/chains/262f0b62c481f7dcfc8be67061d9673203279d0c6658f32a6db099b1c81cf811/applications/fc324ca476fee0c61811e4d437c18f2af46cc3eb6956eb8cbc194902066f481c',
  'http://api.ams.respeer.ai/api/ams/chains/75e519eab9d68400a657aa50dc42f22844d309070a9661fff2dcf1822521f39b/applications/c50d8e6d05a92bec70c4386f427c76ef8f9b797b1f388f6cfa6463cb7d1704eb',
  'http://api.linerameme.fun/api/proxy/chains/2b3741504daaed7385814ca8e822b5cf5332ece47ae3911adbecd4e79c7f84ef/applications/a7f40f05caad440e7e20df91c9d6b32687e85d3bc3bcebd42fc77062f95a98b7',
  'http://api.lineraswap.fun/api/swap/chains/76a921dbb86700cc8866a4f4f95f0bd2b2efca96ab1e46aefc2ea0c8d087956e/applications/1ee987425de91e667076fe118a46639068172e54f3fcaa333b4904e8d73a86f0'
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
