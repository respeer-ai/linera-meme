import { type ams, type meme } from 'src/stores/export'

export interface Token extends ams.Application {
  meme: meme.Meme
}
