/* eslint-disable */
import * as types from './graphql';
import { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';

/**
 * Map of all GraphQL operations in the project.
 *
 * This map has several performance disadvantages:
 * 1. It is not tree-shakeable, so it will include all operations in the project.
 * 2. It is not minifiable, so the string of a GraphQL query will be multiple times inside the bundle.
 * 3. It does not support dead code elimination, so it will add unused operations.
 *
 * Therefore it is highly recommended to use the babel or swc plugin for production.
 * Learn more about it here: https://the-guild.dev/graphql/codegen/plugins/presets/preset-client#reducing-bundle-size
 */
type Documents = {
    "\n  query balances($chainOwners: JSONObject!) {\n    balances(chainOwners: $chainOwners)\n  }\n": typeof types.BalancesDocument,
    "\n  mutation prepareBlob($chainId: ChainId!, $bytes: [Int!]!) {\n    prepareBlob(chainId: $chainId, bytes: $bytes)\n  }\n": typeof types.PrepareBlobDocument,
};
const documents: Documents = {
    "\n  query balances($chainOwners: JSONObject!) {\n    balances(chainOwners: $chainOwners)\n  }\n": types.BalancesDocument,
    "\n  mutation prepareBlob($chainId: ChainId!, $bytes: [Int!]!) {\n    prepareBlob(chainId: $chainId, bytes: $bytes)\n  }\n": types.PrepareBlobDocument,
};

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 *
 *
 * @example
 * ```ts
 * const query = graphql(`query GetUser($id: ID!) { user(id: $id) { name } }`);
 * ```
 *
 * The query argument is unknown!
 * Please regenerate the types.
 */
export function graphql(source: string): unknown;

/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "\n  query balances($chainOwners: JSONObject!) {\n    balances(chainOwners: $chainOwners)\n  }\n"): (typeof documents)["\n  query balances($chainOwners: JSONObject!) {\n    balances(chainOwners: $chainOwners)\n  }\n"];
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "\n  mutation prepareBlob($chainId: ChainId!, $bytes: [Int!]!) {\n    prepareBlob(chainId: $chainId, bytes: $bytes)\n  }\n"): (typeof documents)["\n  mutation prepareBlob($chainId: ChainId!, $bytes: [Int!]!) {\n    prepareBlob(chainId: $chainId, bytes: $bytes)\n  }\n"];

export function graphql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;