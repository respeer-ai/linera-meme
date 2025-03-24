import { gql } from '@apollo/client/core'

export const APPLICATIONS = gql`
  query applications($limit: Int!) {
    applications(limit: $limit)
  }
`
