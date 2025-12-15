import { account, user } from 'src/stores/export'
import { Provider } from './provider'
import { dbModel, rpcModel } from 'src/model'
import { BALANCES, CREATE_MEME, PUBLISH_DATA_BLOB, SWAP } from 'src/graphql'
import { Web3 } from 'web3'
import * as lineraWasm from '../../dist/wasm/linera_wasm'
import { stringify } from 'lossless-json'
import { constants } from 'src/constant'

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

  static swap = async (poolApplicationId: string, variables: Record<string, unknown>) => {
    const publicKey = user.User.publicKey()
    const queryBytes = await lineraWasm.graphql_deserialize_pool_operation(
      SWAP.loc?.source?.body as string,
      stringify(variables) as string,
    )
    return new Promise((resolve, reject) => {
      window.linera
        .request({
          method: 'linera_graphqlMutation',
          params: {
            applicationId: poolApplicationId,
            publicKey,
            query: {
              query: SWAP.loc?.source?.body,
              variables,
              applicationOperationBytes: queryBytes,
            },
            operationName: 'createMeme',
          },
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
}
