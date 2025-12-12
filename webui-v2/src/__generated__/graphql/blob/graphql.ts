/* eslint-disable */
import { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';
export type Maybe<T> = T | null;
export type InputMaybe<T> = T | null | undefined;
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
  /** A Keccak256 value */
  CryptoHash: { input: any; output: any; }
  /** Hash of a Data Blob */
  DataBlobHash: { input: any; output: any; }
  StoreType: { input: any; output: any; }
  /** A timestamp, in microseconds since the Unix epoch */
  Timestamp: { input: any; output: any; }
};

export type BlobData = {
  __typename?: 'BlobData';
  blobHash: Scalars['CryptoHash']['output'];
  createdAt: Scalars['Timestamp']['output'];
  creator: Scalars['Account']['output'];
  dataType: BlobDataType;
  storeType: Scalars['StoreType']['output'];
};

export enum BlobDataType {
  Html = 'HTML',
  Image = 'IMAGE',
  Raw = 'RAW',
  Video = 'VIDEO'
}

export type QueryRoot = {
  __typename?: 'QueryRoot';
  fetch: Array<Scalars['Int']['output']>;
  list: Array<BlobData>;
};


export type QueryRootFetchArgs = {
  blobHash: Scalars['DataBlobHash']['input'];
};


export type QueryRootListArgs = {
  createdAfter?: InputMaybe<Scalars['Timestamp']['input']>;
  createdBefore?: InputMaybe<Scalars['Timestamp']['input']>;
  dataType?: InputMaybe<BlobDataType>;
  limit: Scalars['Int']['input'];
};

export type ListQueryVariables = Exact<{
  createdBefore?: InputMaybe<Scalars['Timestamp']['input']>;
  createdAfter?: InputMaybe<Scalars['Timestamp']['input']>;
  dataType?: InputMaybe<BlobDataType>;
  limit: Scalars['Int']['input'];
}>;


export type ListQuery = { __typename?: 'QueryRoot', list: Array<{ __typename?: 'BlobData', storeType: any, dataType: BlobDataType, blobHash: any, creator: any, createdAt: any }> };


export const ListDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"list"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"createdBefore"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"Timestamp"}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"createdAfter"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"Timestamp"}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"dataType"}},"type":{"kind":"NamedType","name":{"kind":"Name","value":"BlobDataType"}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"limit"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"Int"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"list"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"createdBefore"},"value":{"kind":"Variable","name":{"kind":"Name","value":"createdBefore"}}},{"kind":"Argument","name":{"kind":"Name","value":"createdAfter"},"value":{"kind":"Variable","name":{"kind":"Name","value":"createdAfter"}}},{"kind":"Argument","name":{"kind":"Name","value":"dataType"},"value":{"kind":"Variable","name":{"kind":"Name","value":"dataType"}}},{"kind":"Argument","name":{"kind":"Name","value":"limit"},"value":{"kind":"Variable","name":{"kind":"Name","value":"limit"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"storeType"}},{"kind":"Field","name":{"kind":"Name","value":"dataType"}},{"kind":"Field","name":{"kind":"Name","value":"blobHash"}},{"kind":"Field","name":{"kind":"Name","value":"creator"}},{"kind":"Field","name":{"kind":"Name","value":"createdAt"}}]}}]}}]} as unknown as DocumentNode<ListQuery, ListQueryVariables>;