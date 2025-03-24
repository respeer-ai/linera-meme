export interface TokenMetadata {
  logo: string
  discord: string
  telegram: string
  twitter: string
  website: string
  description: string
  github: string
  mintable: boolean
}

export interface MemeInfo {
  appID: string
  link: string
  totalSupply: string
  name: string
  symbol: string
  decimals: string
  tokenMetadata: TokenMetadata
  balanceOf: string
  allowance: string
  poolId: string
}

export interface NewMemeInfo {
  totalSupply: string
  name: string
  symbol: string
  decimals: string
  logoStoreType: string
  logo: string
  discord: string
  telegram: string
  twitter: string
  website: string
  github: string
  description: string
  mintable: boolean
  initialSupply: string
  initialCurrency: string
  fixedCurrency: boolean
  feePercent: string
}

export interface MemeAppInfoSpec {
  ticker: string
  // eslint-disable-next-line camelcase
  initial_supply: string
  mintable: boolean
}

export interface MemeAppRespInfo {
  // eslint-disable-next-line camelcase
  application_id: string
  // eslint-disable-next-line camelcase
  application_name: string
  // eslint-disable-next-line camelcase
  application_type: string
  // eslint-disable-next-line camelcase
  created_at: number
  description: string
  discord: string
  github: string
  // eslint-disable-next-line camelcase
  logo_store_type: string
  logo: string
  spec: string
  telegram: string
  twitter: string
  website: string
}

export interface MemeAppInfoDisplay {
  poolID: string
  appID: string
  appName: string
  appType: string
  createdAt: number
  description: string
  discord: string
  github: string
  logoStoreType: string
  logo: string
  telegram: string
  twitter: string
  website: string
  ticker: string
  initialSupply: string
  mintable: boolean
  lastTxAt: number
  lastTxZeroAmount: string
  lastTxOneAmount: string
  oneDayZeroAmountVolumn: string
  oneDayOneAmountVolumn: string
  nowPrice: string
  oneDayIncresePercent: string
  poolCreated: boolean
}

export interface ChainOwner {
  // eslint-disable-next-line camelcase
  chain_id: string
  owner: string
}

export interface OwnerBalance {
  owner: ChainOwner
  balance: number
}

export interface InitPoolLiquidity {
  amount0Initial: string
  amount1Initial: string
  amount0Virtual: string
  amount1Virtual: string
}

export interface ChainApp {
  id: string
  link: string
}

export interface BlobInfo {
  id: number
  storeType: string
  blobHash: string
  dataType: string
  createdAt: number
  creator: string
  thumbnail: string
}
