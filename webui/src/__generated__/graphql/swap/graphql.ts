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
  /** A non-negative amount of tokens. */
  Amount: { input: any; output: any; }
  /** A unique identifier for a user application */
  ApplicationId: { input: any; output: any; }
  /** The unique identifier (UID) of a chain. This is currently computed as the hash value of a ChainDescription. */
  ChainId: { input: any; output: any; }
  /** A timestamp, in microseconds since the Unix epoch */
  Timestamp: { input: any; output: any; }
  Transaction: { input: any; output: any; }
};

export type Pool = {
  __typename?: 'Pool';
  createdAt: Scalars['Timestamp']['output'];
  creator: Scalars['Account']['output'];
  latestTransaction?: Maybe<Scalars['Transaction']['output']>;
  poolApplication: Scalars['Account']['output'];
  poolId: Scalars['Int']['output'];
  reserve0?: Maybe<Scalars['Amount']['output']>;
  reserve1?: Maybe<Scalars['Amount']['output']>;
  token0: Scalars['ApplicationId']['output'];
  token0Price?: Maybe<Scalars['Amount']['output']>;
  token1?: Maybe<Scalars['ApplicationId']['output']>;
  token1Price?: Maybe<Scalars['Amount']['output']>;
};

export type QueryRoot = {
  __typename?: 'QueryRoot';
  creatorChainId: Scalars['ChainId']['output'];
  poolId: Scalars['Int']['output'];
  pools: Array<Pool>;
};

export type PoolsQueryVariables = Exact<{ [key: string]: never; }>;


export type PoolsQuery = { __typename?: 'QueryRoot', pools: Array<{ __typename?: 'Pool', creator: any, poolId: number, token0: any, token1?: any | null, poolApplication: any, latestTransaction?: any | null, token0Price?: any | null, token1Price?: any | null, reserve0?: any | null, reserve1?: any | null, createdAt: any }> };


export const PoolsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"pools"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"pools"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"creator"}},{"kind":"Field","name":{"kind":"Name","value":"poolId"}},{"kind":"Field","name":{"kind":"Name","value":"token0"}},{"kind":"Field","name":{"kind":"Name","value":"token1"}},{"kind":"Field","name":{"kind":"Name","value":"poolApplication"}},{"kind":"Field","name":{"kind":"Name","value":"latestTransaction"}},{"kind":"Field","name":{"kind":"Name","value":"token0Price"}},{"kind":"Field","name":{"kind":"Name","value":"token1Price"}},{"kind":"Field","name":{"kind":"Name","value":"reserve0"}},{"kind":"Field","name":{"kind":"Name","value":"reserve1"}},{"kind":"Field","name":{"kind":"Name","value":"createdAt"}}]}}]}}]} as unknown as DocumentNode<PoolsQuery, PoolsQueryVariables>;