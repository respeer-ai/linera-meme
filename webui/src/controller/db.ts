import Dexie, { type EntityTable } from 'dexie'
import { dbModel } from '../model'

export const dbBase = new Dexie('KLineDatabase') as Dexie & {
  oneMMs: EntityTable<dbModel.OneMM, 'id'>
}

dbBase.version(1).stores({
  oneMMs: '++id, name, msg'
})

export const dbMeme = new Dexie('MemeDatabase') as Dexie & {
  memes: EntityTable<dbModel.ChainMeme, 'id'>
}

dbMeme.version(1).stores({
  memes: '++id, chain_id, meme_id'
})
