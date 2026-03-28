import { gql } from '@apollo/client/core'

export const BALANCES = gql`
  query balances($chainOwners: [ChainOwners!]!) {
    balances(chainOwners: $chainOwners)
  }
`

export const NOTIFICATIONS = gql`
  subscription notifications($chainId: ChainId!) {
    notifications(chainId: $chainId)
  }
`

export const BLOCK_MATERIAL_WITH_DEFAULT_CHAIN = gql`
  query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {
    blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {
      incomingBundles {
        action
        bundle {
          height
          timestamp
          certificateHash
          transactionIndex
          messages {
            authenticatedSigner
            grant
            refundGrantTo
            kind
            index
            message
            messageMetadata {
              messageType
              applicationId
              userBytesHex
              systemMessage {
                systemMessageType
                credit {
                  target
                  amount
                  source
                }
                withdraw {
                  owner
                  amount
                  recipient
                }
              }
            }
          }
        }
        origin
      }
      localTime
      round
    }
  }
`

export const ESTIMATE_GAS = gql`
  query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {
    estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)
  }
`
