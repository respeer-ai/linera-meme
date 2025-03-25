import { gql } from '@apollo/client/core'

export const CREATE_MEME = gql`
  mutation createMeme(
    $memeInstantiationArgument: MemeInstantiationArgument!
    $memeParameters: MemeParameters
  ) {
    createMeme(
      memeInstantiationArgument: $memeInstantiationArgument
      memeParameters: $memeParameters
    )
  }
`
