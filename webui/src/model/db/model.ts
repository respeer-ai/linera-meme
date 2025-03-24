import { _hex } from '../../utils'
import { sha3 } from 'hash-wasm'

export interface OneMM {
  id?: number
  name: string
  msg: string
}

export const ownerFromPublicKey = (publicKey: string) => {
  const publicKeyBytes = _hex.toBytes(publicKey)
  const typeNameBytes = new TextEncoder().encode('PublicKey::')
  const bytes = new Uint8Array([...typeNameBytes, ...publicKeyBytes])
  return sha3(bytes, 256)
}

export interface ChainMeme {
  id?: number
  chain_id: string
  meme_id: string
}
