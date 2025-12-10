import { Interval } from '../../stores/kline/const'
import { Point } from '../../stores/kline/types'
import { _hex } from '../../utils'
import { keccak } from 'hash-wasm'
import { TransactionExt } from '../../stores/transaction/types'

export const ownerFromPublicKey = async (publicKey: string) => {
  const publicKeyBytes = _hex.toBytes(publicKey)
  const typeNameBytes = new TextEncoder().encode('Ed25519PublicKey::')
  const bytes = new Uint8Array([...typeNameBytes, ...publicKeyBytes])
  return await keccak(bytes, 256)
}

export interface KlinePoint extends Point {
  id?: number
  token0: string
  token1: string
  interval: Interval
}

export interface _Transaction extends TransactionExt {
  id?: number
  token0: string
  token1: string
}
