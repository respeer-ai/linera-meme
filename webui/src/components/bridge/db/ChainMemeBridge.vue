<script setup lang='ts'>
import { dbMeme } from 'src/controller'
import { dbModel } from 'src/model'

const add = async (chain_id: string, meme_id: string) => {
  await dbMeme.memes.add({
    chain_id,
    meme_id
  } as dbModel.ChainMeme)
}

const GetMemeID = async (id: number) => {
  return await dbMeme.memes.get(id)
}

defineExpose({
  add,
  GetMemeID
})

</script>
