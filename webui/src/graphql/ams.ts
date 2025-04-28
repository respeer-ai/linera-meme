import { gql } from '@apollo/client/core'

export const APPLICATIONS = gql`
  query applications(createdAfter: Int, $limit: Int!) {
    applications(createdAfter: $createdAfter, limit: $limit)
  }
`
