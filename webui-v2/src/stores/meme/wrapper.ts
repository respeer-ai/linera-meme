import { constants } from 'src/constant'
import { _Account, type Account } from '../account'
import { NotifyType } from '../notify'
import { useUserStore } from '../user'
import { useMemeStore } from './store'

const _user = useUserStore()
const _meme = useMemeStore()

export class MemeWrapper {
  static balanceOfMeme = async (tokenApplication: Account, done: (balance: string) => void) => {
    const owner = await _user.account()
    if (!owner.owner || !tokenApplication.owner || !tokenApplication.chain_id) return
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
      (error: boolean, balance?: string) => {
        if (error) return
        done(balance as string)
      },
    )
  }

  static applicationUrl = (tokenApplication: Account) => {
    return _Account.applicationUrl(constants.PROXY_URL, tokenApplication)
  }
}
