import { gql } from '@apollo/client/core'

export const MEME_APPLICATIONS = gql`
  query memeApplications {
    memeApplications
  }
`
