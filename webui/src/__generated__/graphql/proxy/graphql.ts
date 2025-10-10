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
  /** A unique identifier for an application module */
  ModuleId: { input: any; output: any; }
  /** A timestamp, in microseconds since the Unix epoch */
  Timestamp: { input: any; output: any; }
};

export type Chain = {
  __typename?: 'Chain';
  chainId: Scalars['ChainId']['output'];
  createdAt: Scalars['Timestamp']['output'];
  token?: Maybe<Scalars['ApplicationId']['output']>;
};

export type QueryRoot = {
  __typename?: 'QueryRoot';
  creatorChainId: Scalars['ChainId']['output'];
  genesisMiners: Array<Scalars['Account']['output']>;
  memeApplicationIds: Array<Maybe<Scalars['ApplicationId']['output']>>;
  memeApplications: Array<Chain>;
  memeBytecodeId: Scalars['ModuleId']['output'];
  memeChains: Array<Chain>;
  miners: Array<Scalars['Account']['output']>;
};

export type MemeApplicationsQueryVariables = Exact<{ [key: string]: never; }>;


export type MemeApplicationsQuery = { __typename?: 'QueryRoot', memeApplications: Array<{ __typename?: 'Chain', chainId: any, createdAt: any, token?: any | null }> };

export type GenesisMinersQueryVariables = Exact<{ [key: string]: never; }>;


export type GenesisMinersQuery = { __typename?: 'QueryRoot', genesisMiners: Array<any> };


export const MemeApplicationsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"memeApplications"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"memeApplications"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"chainId"}},{"kind":"Field","name":{"kind":"Name","value":"createdAt"}},{"kind":"Field","name":{"kind":"Name","value":"token"}}]}}]}}]} as unknown as DocumentNode<MemeApplicationsQuery, MemeApplicationsQueryVariables>;
export const GenesisMinersDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"genesisMiners"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"genesisMiners"}}]}}]} as unknown as DocumentNode<GenesisMinersQuery, GenesisMinersQueryVariables>;