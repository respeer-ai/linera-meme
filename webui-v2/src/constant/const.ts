import * as domain from './domain'

export const formalizeSchema = (url: string) => {
  url = url.replace(
    'http://',
    process.env.NODE_ENV === 'production' ? 'https://' : 'https://'
  )
  url = url.replace(
    'ws://',
    process.env.NODE_ENV === 'production' ? 'wss://' : 'wss://'
  )
  return url
}

const URLS = [
  `http://api.${domain.SUB_DOMAIN}blobgateway.com/api/blobs/chains/${domain.BLOB_GATEWAY_CHAIN_ID}/applications/${domain.BLOB_GATEWAY_APPLICATION_ID}`,
  `http://api.${domain.SUB_DOMAIN}ams.respeer.ai/api/ams/chains/${domain.AMS_CHAIN_ID}/applications/${domain.AMS_APPLICATION_ID}`,
  `http://api.${domain.SUB_DOMAIN}linerameme.fun/api/proxy/chains/${domain.PROXY_CHAIN_ID}/applications/${domain.PROXY_APPLICATION_ID}`,
  `http://api.${domain.SUB_DOMAIN}lineraswap.fun/api/swap/chains/${domain.SWAP_CHAIN_ID}/applications/${domain.SWAP_APPLICATION_ID}`,
  `http://api.${domain.SUB_DOMAIN}rpc.respeer.ai/api/rpc`,
  `ws://api.${domain.SUB_DOMAIN}rpc.respeer.ai/api/rpc/ws`,
  `http://api.${domain.SUB_DOMAIN}kline.lineraswap.fun/api/kline`,
  `ws://api.${domain.SUB_DOMAIN}kline.lineraswap.fun/api/kline/ws`,
  `http://api.${domain.SUB_DOMAIN}lineraswap.fun/api/swap`,
  `http://api.${domain.SUB_DOMAIN}linerameme.fun/api/proxy`,
  `ws://api.${domain.SUB_DOMAIN}linerameme.fun/api/proxy/ws`,
  `http://api.${domain.SUB_DOMAIN}ams.respeer.ai/api/ams`,
  `ws://api.${domain.SUB_DOMAIN}ams.respeer.ai/api/ams/ws`,
  `ws://api.${domain.SUB_DOMAIN}lineraswap.fun/api/swap/ws`
]

export const APPLICATION_URLS = {
  BLOB_GATEWAY: formalizeSchema(URLS[0] as string),
  AMS: formalizeSchema(URLS[1] as string),
  PROXY: formalizeSchema(URLS[2] as string),
  SWAP: formalizeSchema(URLS[3] as string)
}

export const RPC_URL = formalizeSchema(URLS[4] as string)
export const RPC_WS_URL = formalizeSchema(URLS[5] as string)
export const KLINE_HTTP_URL = formalizeSchema(URLS[6] as string)
export const KLINE_WS_URL = formalizeSchema(URLS[7] as string)
export const SWAP_URL = formalizeSchema(URLS[8] as string)
export const SWAP_WS_URL = formalizeSchema(URLS[13] as string)
export const PROXY_URL = formalizeSchema(URLS[9] as string)
export const PROXY_WS_URL = formalizeSchema(URLS[10] as string)
export const AMS_URL = formalizeSchema(URLS[11] as string)
export const AMS_WS_URL = formalizeSchema(URLS[12] as string)

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


export const X_LOGO = 'https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/x.svg'
export const DISCORD_LOGO = 'https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/discord.svg'
export const GITHUB_LOGO = 'https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/github.svg'
export const TELEGRAM_LOGO = 'https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/telegram.svg'

export const METAMASK_LOGO = 'https://icon-sets.iconify.design/logos/metamask.svg'
export const CHECKO_LOGO = 'https://github.com/respeer-ai/linera-wallet/blob/master/public/favicon.png?raw=true'
