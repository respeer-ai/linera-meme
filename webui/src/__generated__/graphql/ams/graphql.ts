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
  /** A unique identifier for a user application */
  ApplicationId: { input: any; output: any; }
  Metadata: { input: any; output: any; }
  /** A timestamp, in microseconds since the Unix epoch */
  Timestamp: { input: any; output: any; }
};

export type QueryRoot = {
  __typename?: 'QueryRoot';
  application?: Maybe<Scalars['Metadata']['output']>;
  applications: Array<Scalars['Metadata']['output']>;
};


export type QueryRootApplicationArgs = {
  applicationId: Scalars['ApplicationId']['input'];
};


export type QueryRootApplicationsArgs = {
  applicationIds?: InputMaybe<Array<Scalars['ApplicationId']['input']>>;
  applicationType?: InputMaybe<Scalars['String']['input']>;
  createdAfter?: InputMaybe<Scalars['Timestamp']['input']>;
  createdBefore?: InputMaybe<Scalars['Timestamp']['input']>;
  limit: Scalars['Int']['input'];
  spec?: InputMaybe<Scalars['String']['input']>;
};

export type ApplicationsQueryVariables = Exact<{
  limit: Scalars['Int']['input'];
}>;


export type ApplicationsQuery = { __typename?: 'QueryRoot', applications: Array<any> };


export const ApplicationsDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"applications"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"limit"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"Int"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"applications"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"limit"},"value":{"kind":"Variable","name":{"kind":"Name","value":"limit"}}}]}]}}]} as unknown as DocumentNode<ApplicationsQuery, ApplicationsQueryVariables>;