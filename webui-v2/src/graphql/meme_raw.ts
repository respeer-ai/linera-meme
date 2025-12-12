import { gql } from '@apollo/client/core';

export const BALANCE_OF = gql`
  query balanceOf($owner: String!) {
    balanceOf(owner: $owner)
  }
`;
