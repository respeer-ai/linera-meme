import { gql } from '@apollo/client/core'

export const MEME_APPLICATIONS = gql`
  query memeApplications {
    memeApplications {
      chainId
      messageId
      createdAt
      token
    }
  }
`

export const GENESIS_MINERS = gql`
  query genesisMiners {
    genesisMiners
  }
`
