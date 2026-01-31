import { constants } from 'src/constant'
import { _Account, type Account } from '../account'
import { NotifyType } from '../notify'
import { useUserStore } from '../user'
import { useMemeStore } from './store'

const _user = useUserStore()
const _meme = useMemeStore()

export class MemeWrapper {
  static balanceOfMeme = async (
    tokenApplication: Account,
    done: (balance: string) => void,
    error?: () => void,
  ) => {
    const owner = await _user.account()
    if (!owner.owner || !tokenApplication.owner || !tokenApplication.chain_id) return error?.()
    const owenrDescription = _Account.accountDescription(owner)

    _meme.balanceOf(
      {
        owner: owenrDescription,
        Message: {
          Error: {
            Title: 'Balance of meme',
            Message: 'Failed get balance of meme',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      tokenApplication,
      (_error: boolean, balance?: string) => {
        if (_error) return error?.()
        done(balance as string)
      },
    )
  }

  static balancesOfMeme = (
    tokenApplication: Account,
    done: (balances: Record<string, string>) => void,
    error?: () => void,
  ) => {
    if (!tokenApplication.owner || !tokenApplication.chain_id) return error?.()

    _meme.balances(
      {
        Message: {
          Error: {
            Title: 'Balances of meme',
            Message: 'Failed get balances of meme',
            Popup: true,
            Type: NotifyType.Error,
          },
        },
      },
      tokenApplication,
      (_error: boolean, balances?: Record<string, string>) => {
        if (_error) return error?.()
        done(balances as Record<string, string>)
      },
    )
  }

  static applicationUrl = (tokenApplication: Account) => {
    return _Account.applicationUrl(constants.PROXY_URL, tokenApplication)
  }

  static initializeMeme = (chainId: string) => _meme.initializeMeme(chainId)
  static finalizeMeme = (chainId: string) => _meme.finalizeMeme(chainId)

  static blockHash = (chainId: string) => _meme.blockHashs.get(chainId)
}
