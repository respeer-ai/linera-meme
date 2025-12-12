import { gql } from '@apollo/client/core';

export const APPLICATIONS = gql`
  query applications($createdBefore: Timestamp, $createdAfter: Timestamp, $limit: Int!) {
    applications(createdBefore: $createdBefore, createdAfter: $createdAfter, limit: $limit)
  }
`;
