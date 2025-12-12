import { gql } from '@apollo/client/core';

export const LIST = gql`
  query list(
    $createdBefore: Timestamp
    $createdAfter: Timestamp
    $dataType: BlobDataType
    $limit: Int!
  ) {
    list(
      createdBefore: $createdBefore
      createdAfter: $createdAfter
      dataType: $dataType
      limit: $limit
    ) {
      storeType
      dataType
      blobHash
      creator
      createdAt
    }
  }
`;
