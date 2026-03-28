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
    "\n  query balances($chainOwners: [ChainOwners!]!) {\n    balances(chainOwners: $chainOwners)\n  }\n": typeof types.BalancesDocument,
    "\n  subscription notifications($chainId: ChainId!) {\n    notifications(chainId: $chainId)\n  }\n": typeof types.NotificationsDocument,
    "\n  query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {\n    blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {\n      incomingBundles {\n        action\n        bundle {\n          height\n          timestamp\n          certificateHash\n          transactionIndex\n          messages {\n            authenticatedSigner\n            grant\n            refundGrantTo\n            kind\n            index\n            message\n            messageMetadata {\n              messageType\n              applicationId\n              userBytesHex\n              systemMessage {\n                systemMessageType\n                credit {\n                  target\n                  amount\n                  source\n                }\n                withdraw {\n                  owner\n                  amount\n                  recipient\n                }\n              }\n            }\n          }\n        }\n        origin\n      }\n      localTime\n      round\n    }\n  }\n": typeof types.BlockMaterialWithDefaultChainDocument,
    "\n  query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {\n    estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)\n  }\n": typeof types.EstimateGasDocument,
};
const documents: Documents = {
    "\n  query balances($chainOwners: [ChainOwners!]!) {\n    balances(chainOwners: $chainOwners)\n  }\n": types.BalancesDocument,
    "\n  subscription notifications($chainId: ChainId!) {\n    notifications(chainId: $chainId)\n  }\n": types.NotificationsDocument,
    "\n  query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {\n    blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {\n      incomingBundles {\n        action\n        bundle {\n          height\n          timestamp\n          certificateHash\n          transactionIndex\n          messages {\n            authenticatedSigner\n            grant\n            refundGrantTo\n            kind\n            index\n            message\n            messageMetadata {\n              messageType\n              applicationId\n              userBytesHex\n              systemMessage {\n                systemMessageType\n                credit {\n                  target\n                  amount\n                  source\n                }\n                withdraw {\n                  owner\n                  amount\n                  recipient\n                }\n              }\n            }\n          }\n        }\n        origin\n      }\n      localTime\n      round\n    }\n  }\n": types.BlockMaterialWithDefaultChainDocument,
    "\n  query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {\n    estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)\n  }\n": types.EstimateGasDocument,
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
export function graphql(source: "\n  query balances($chainOwners: [ChainOwners!]!) {\n    balances(chainOwners: $chainOwners)\n  }\n"): (typeof documents)["\n  query balances($chainOwners: [ChainOwners!]!) {\n    balances(chainOwners: $chainOwners)\n  }\n"];
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "\n  subscription notifications($chainId: ChainId!) {\n    notifications(chainId: $chainId)\n  }\n"): (typeof documents)["\n  subscription notifications($chainId: ChainId!) {\n    notifications(chainId: $chainId)\n  }\n"];
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "\n  query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {\n    blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {\n      incomingBundles {\n        action\n        bundle {\n          height\n          timestamp\n          certificateHash\n          transactionIndex\n          messages {\n            authenticatedSigner\n            grant\n            refundGrantTo\n            kind\n            index\n            message\n            messageMetadata {\n              messageType\n              applicationId\n              userBytesHex\n              systemMessage {\n                systemMessageType\n                credit {\n                  target\n                  amount\n                  source\n                }\n                withdraw {\n                  owner\n                  amount\n                  recipient\n                }\n              }\n            }\n          }\n        }\n        origin\n      }\n      localTime\n      round\n    }\n  }\n"): (typeof documents)["\n  query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {\n    blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {\n      incomingBundles {\n        action\n        bundle {\n          height\n          timestamp\n          certificateHash\n          transactionIndex\n          messages {\n            authenticatedSigner\n            grant\n            refundGrantTo\n            kind\n            index\n            message\n            messageMetadata {\n              messageType\n              applicationId\n              userBytesHex\n              systemMessage {\n                systemMessageType\n                credit {\n                  target\n                  amount\n                  source\n                }\n                withdraw {\n                  owner\n                  amount\n                  recipient\n                }\n              }\n            }\n          }\n        }\n        origin\n      }\n      localTime\n      round\n    }\n  }\n"];
/**
 * The graphql function is used to parse GraphQL queries into a document that can be used by GraphQL clients.
 */
export function graphql(source: "\n  query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {\n    estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)\n  }\n"): (typeof documents)["\n  query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {\n    estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)\n  }\n"];

export function graphql(source: string) {
  return (documents as any)[source] ?? {};
}

export type DocumentType<TDocumentNode extends DocumentNode<any, any>> = TDocumentNode extends DocumentNode<  infer TType,  any>  ? TType  : never;