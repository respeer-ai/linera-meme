/* eslint-disable */
import { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';
export type Maybe<T> = T | null;
export type InputMaybe<T> = Maybe<T>;
export type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
export type MakeOptional<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]?: Maybe<T[SubKey]> };
export type MakeMaybe<T, K extends keyof T> = Omit<T, K> & { [SubKey in K]: Maybe<T[SubKey]> };
export type MakeEmpty<T extends { [key: string]: unknown }, K extends keyof T> = { [_ in K]?: never };
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
/** All built-in and custom scalars, mapped to their actual values */
export type Scalars = {
  ID: { input: string; output: string; }
  String: { input: string; output: string; }
  Boolean: { input: boolean; output: boolean; }
  Int: { input: number; output: number; }
  Float: { input: number; output: number; }
  /** An account */
  Account: { input: any; output: any; }
  /** A unique identifier for a user application */
  ApplicationId: { input: any; output: any; }
  /** The unique identifier (UID) of a chain. This is currently computed as the hash value of a ChainDescription. */
  ChainId: { input: any; output: any; }
  /** The index of a message in a chain */
  MessageId: { input: any; output: any; }
  Transaction: { input: any; output: any; }
};

export type Pool = {
  __typename?: 'Pool';
  poolApplication: Scalars['Account']['output'];
  poolId: Scalars['Int']['output'];
  token0: Scalars['ApplicationId']['output'];
  token1?: Maybe<Scalars['ApplicationId']['output']>;
};

export type QueryRoot = {
  __typename?: 'QueryRoot';
  creatorChainId: Scalars['ChainId']['output'];
  latestTransactions: Array<TransactionExt>;
  poolChainCreationMessages: Array<Scalars['MessageId']['output']>;
  poolId: Scalars['Int']['output'];
  pools: Array<Pool>;
};

export type TransactionExt = {
  __typename?: 'TransactionExt';
  token0: Scalars['ApplicationId']['output'];
  token1?: Maybe<Scalars['ApplicationId']['output']>;
  transaction: Scalars['Transaction']['output'];
};

export type PoolsQueryVariables = Exact<{ [key: string]: never; }>;


export type PoolsQuery = { __typename?: 'QueryRoot', pools: Array<{ __typename?: 'Pool', poolId: number, token0: any, token1?: any | null }> };

export type LatestTransactionsQueryVariables = Exact<{ [key: string]: never; }>;


export type LatestTransactionsQuery = { __typename?: 'QueryRoot', latestTransactions: Array<{ __typename?: 'TransactionExt', token0: any, token1?: any | null, transaction: any }> };


export const PoolsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"pools"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"pools"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"poolId"}},{"kind":"Field","name":{"kind":"Name","value":"token0"}},{"kind":"Field","name":{"kind":"Name","value":"token1"}}]}}]}}]} as unknown as DocumentNode<PoolsQuery, PoolsQueryVariables>;
export const LatestTransactionsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"latestTransactions"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"latestTransactions"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"token0"}},{"kind":"Field","name":{"kind":"Name","value":"token1"}},{"kind":"Field","name":{"kind":"Name","value":"transaction"}}]}}]}}]} as unknown as DocumentNode<LatestTransactionsQuery, LatestTransactionsQueryVariables>;