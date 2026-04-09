import { account, user } from 'src/stores/export'
import { Provider } from './provider'
import { dbModel, rpcModel } from 'src/model'
import {
  ADD_LIQUIDITY,
  BALANCES,
  BLOCK_MATERIAL_WITH_DEFAULT_CHAIN,
  CREATE_POOL,
  CREATE_MEME,
  ESTIMATE_GAS,
  PUBLISH_DATA_BLOB,
  SWAP,
} from 'src/graphql'
import { ApolloClient } from '@apollo/client/core'
import axios from 'axios'
import { Web3 } from 'web3'
import * as lineraWasm from '../../dist/wasm/linera_wasm'
import { parse, stringify } from 'lossless-json'
import { getClientOptions } from 'src/apollo'
import { constants } from 'src/constant'
import { graphqlResult } from 'src/utils'

export class CheCko {
  static subscribe = (
    onSubscribed: (subscriptionId: string) => void,
    onData: (walletType: user.WalletType, msg: unknown) => void,
  ) => {
    window.linera
      ?.request({
        method: 'linera_subscribe',
      })
      .then((_subscriptionId) => {
        onSubscribed(_subscriptionId as string)
        window.linera.on('message', (msg: unknown) => {
          onData(user.WalletType.CheCko, msg)
        })
      })
      .catch((e) => {
        console.log('Fail subscribe', e)
      })
  }

  static unsubscribe = (subscriptionId: string) => {
    void window.linera?.request({
      method: 'linera_unsubscribe',
      params: [subscriptionId],
    })
  }

  static getProviderState = async () => {
    const chainId = await Provider.getProviderState(window.linera)
    user.User.setChainId(chainId)
    user.User.setWalletConnectedType(user.WalletType.CheCko)
  }

  static getBalance = async () => {
    // TODO: implement with web3 api

    const publicKey = user.User.publicKey()
    const chainId = user.User.chainId()

    if (!publicKey) return
    const owner = await dbModel.ownerFromPublicKey(publicKey)
    window.linera
      .request({
        method: 'linera_graphqlQuery',
        params: {
          publicKey,
          query: {
            query: BALANCES.loc?.source?.body,
            variables: {
              chainOwners: [
                {
                  chainId,
                  owners: [account._Account.formalizeOwner(owner)],
                },
              ],
              chainId,
              publicKey,
            },
          },
        },
      })
      .then((result) => {
        const balances = result as rpcModel.Balances
        user.User.setChainBalance(rpcModel.chainBalance(balances, chainId))
        user.User.setAccountBalance(
          rpcModel.ownerBalance(balances, chainId, account._Account.formalizeOwner(owner)),
        )
      })
      .catch((e) => {
        console.log(e)
      })
  }

  static connect = async () => {
    if (!window.linera) {
      return window.open('https://github.com/respeer-ai/linera-wallet.git')
    }

    const web3 = new Web3(window.linera)
    await web3.eth.requestAccounts()

    await CheCko.getProviderState()
  }

  static swapOperation = async (poolApplicationId: string, variables: Record<string, unknown>) => {
    const publicKey = user.User.publicKey()
    const queryBytes = await lineraWasm.graphql_deserialize_pool_operation(
      SWAP.loc?.source?.body as string,
      stringify(variables) as string,
    )
    return {
      applicationId: poolApplicationId,
      publicKey,
      query: {
        query: SWAP.loc?.source?.body,
        variables,
        applicationOperationBytes: queryBytes,
      },
      operationName: 'swap',
    }
  }

  static swap = async (poolApplicationId: string, variables: Record<string, unknown>) => {
    const operationParams = await CheCko.swapOperation(poolApplicationId, variables)

    return new Promise((resolve, reject) => {
      window.linera
        .request({
          method: 'linera_graphqlMutation',
          params: operationParams,
        })
        .then((hash) => {
          resolve(hash as string)
        })
        .catch((e) => {
          reject(new Error(e))
        })
    })
  }

  static createPoolOperation = async (
    swapApplicationId: string,
    variables: Record<string, unknown>,
  ) => {
    const publicKey = user.User.publicKey()
    const queryBytes = await lineraWasm.graphql_deserialize_swap_operation(
      CREATE_POOL.loc?.source?.body as string,
      stringify(variables) as string,
    )
    return {
      applicationId: swapApplicationId,
      publicKey,
      query: {
        query: CREATE_POOL.loc?.source?.body,
        variables,
        applicationOperationBytes: queryBytes,
      },
      operationName: 'createPool',
    }
  }

  static createPool = async (swapApplicationId: string, variables: Record<string, unknown>) => {
    const operationParams = await CheCko.createPoolOperation(swapApplicationId, variables)

    return new Promise((resolve, reject) => {
      window.linera
        .request({
          method: 'linera_graphqlMutation',
          params: operationParams,
        })
        .then((hash) => {
          resolve(hash as string)
        })
        .catch((e) => {
          reject(new Error(e))
        })
    })
  }

  static addLiquidityOperation = async (
    poolApplicationId: string,
    variables: Record<string, unknown>,
  ) => {
    const publicKey = user.User.publicKey()
    const queryBytes = await lineraWasm.graphql_deserialize_pool_operation(
      ADD_LIQUIDITY.loc?.source?.body as string,
      stringify(variables) as string,
    )
    return {
      applicationId: poolApplicationId,
      publicKey,
      query: {
        query: ADD_LIQUIDITY.loc?.source?.body,
        variables,
        applicationOperationBytes: queryBytes,
      },
      operationName: 'addLiquidity',
    }
  }

  static addLiquidity = async (poolApplicationId: string, variables: Record<string, unknown>) => {
    const operationParams = await CheCko.addLiquidityOperation(poolApplicationId, variables)

    return new Promise((resolve, reject) => {
      window.linera
        .request({
          method: 'linera_graphqlMutation',
          params: operationParams,
        })
        .then((hash) => {
          resolve(hash as string)
        })
        .catch((e) => {
          reject(new Error(e))
        })
    })
  }

  static blobHash = async (logoBytes: number[]) => {
    return await lineraWasm.blob_hash(`[${logoBytes.toString()}]`)
  }

  static publishDataBlob = async (logoBytes: number[], blobHash: string) => {
    const publicKey = user.User.publicKey()
    const chainId = user.User.chainId()

    return new Promise((resolve, reject) => {
      window.linera
        .request({
          method: 'linera_graphqlMutation',
          params: {
            publicKey,
            query: {
              query: PUBLISH_DATA_BLOB.loc?.source?.body,
              variables: {
                chainId,
                blobHash,
              },
              blobBytes: [JSON.stringify(logoBytes)],
            },
            operationName: 'publishDataBlob',
          },
        })
        .then((blobHash) => {
          resolve(blobHash as string)
        })
        .catch((e) => {
          reject(new Error(e))
        })
    })
  }

  static createMeme = async (
    argument: unknown,
    parameters: unknown,
    variables: Record<string, unknown>,
  ) => {
    const publicKey = user.User.publicKey()
    const queryBytes = await lineraWasm.graphql_deserialize_proxy_operation(
      CREATE_MEME.loc?.source?.body as string,
      stringify(variables) as string,
    )

    const owner = await dbModel.ownerFromPublicKey(publicKey)
    const chainId = user.User.chainId()
    console.log(`Creating meme owner ${owner}, publicKey ${publicKey}, chain ${chainId}`)

    return (await window.linera.request({
      method: 'linera_graphqlMutation',
      params: {
        applicationId: constants.applicationId(constants.APPLICATION_URLS.PROXY),
        publicKey,
        query: {
          query: CREATE_MEME.loc?.source?.body,
          variables: {
            memeInstantiationArgument: stringify(argument),
            memeParameters: stringify(parameters),
          },
          applicationOperationBytes: queryBytes,
        },
        operationName: 'createMeme',
      },
    })) as string
  }

  static estimateSwapGas = async (
    poolApplicationId: string,
    variables: Record<string, unknown>,
  ) => {
    return await CheCko.estimateGas(await CheCko.swapOperation(poolApplicationId, variables))
  }

  static blockMaterialWithDefaultChain = async () => {
    const apolloClient = new ApolloClient(getClientOptions(constants.RPC_URL))
    const { data } = await apolloClient.query({
      query: BLOCK_MATERIAL_WITH_DEFAULT_CHAIN,
      variables: {
        chainId: user.User.chainId(),
        maxPendingMessages: 2,
      },
      fetchPolicy: 'network-only',
    })

    return data.blockMaterialWithDefaultChain
  }

  static estimateGas = async (params: Record<string, unknown>) => {
    params.operationName = 'estimateGas'

    return (await window.linera.request({
      method: 'eth_estimateGas',
      params,
    })) as string
  }

  static estimateGasWithRpc = async (params: Record<string, unknown>) => {
    const query = params.query as Record<string, unknown>
    const candidate = await CheCko.blockMaterialWithDefaultChain()
    const operation = {
      User: {
        applicationId: params.applicationId,
        bytes: JSON.parse(query.applicationOperationBytes as string) as number[],
      },
    }

    const res = await axios.post(
      constants.RPC_URL,
      stringify({
        query: ESTIMATE_GAS.loc?.source?.body,
        variables: {
          chainId: user.User.chainId(),
          blockMaterial: {
            operations: [operation],
            blobBytes: [],
            candidate,
          },
        },
        operationName: 'estimateGas',
      }),
      {
        responseType: 'text',
        transformResponse: [(data) => data as string],
      },
    )

    const dataString = graphqlResult.rootData(res) as string
    const data = parse(dataString) as Record<string, unknown>
    const errors = data.errors as unknown[] | undefined
    if (errors?.length) {
      return Promise.reject(new Error(stringify(errors)))
    }

    return ((data.data as Record<string, unknown>)?.estimateGas || '') as string
  }
}
