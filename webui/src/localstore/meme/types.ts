import { Account } from '../account'
import { StoreType } from '../store'

// TODO: export those from meme application
export interface Metadata {
  logoStoreType: StoreType
  logo?: string
  description: string
  twitter?: string
  telegram?: string
  discord?: string
  website?: string
  github?: string
  liveStream?: string
}

export interface Liquidity {
  fungibleAmount: string
  nativeAmount: string
}

export interface Meme {
  initialSupply: string
  totalSupply: string
  name: string
  ticker: string
  decimals: number
  metadata: Metadata
  virtualInitialLiquidity: boolean
  initialLiquidity?: Liquidity
}

export interface InstantiationArgument {
  meme: Meme
  blobGatewayApplicationId?: string
  amsApplicationId?: string
}

export interface MemeParameters {
  creator: Account
  initialLiquidity?: Liquidity
  virtualInitialLiquidity: boolean
  swapCreatorChainId: string
}
