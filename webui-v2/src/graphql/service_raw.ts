import { gql } from '@apollo/client/core';

export const PUBLISH_DATA_BLOB = gql`
  mutation publishDataBlob($chainId: ChainId!, $blobHash: CryptoHash!) {
    publishDataBlob(chainId: $chainId, blobHash: $blobHash)
  }
`;
