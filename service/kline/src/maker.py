import argparse


from swap import Swap
from meme import Meme
from wallet import Wallet
from trader import Trader


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--wallet-host', type=str, default='localhost:8080', help='Host of wallet service')
    parser.add_argument('--meme-host', type=str, default='api.linerameme.fun', help='Host of meme service')

    args = parser.parse_args()

    _swap = Swap(args.swap_host, args.swap_application_id)
    _swap.get_swap_chain()
    _swap.get_swap_application()

    _meme = Meme(args.meme_host)
    _wallet = Wallet(args.wallet_host)

    _trader = Trader(_swap, _wallet, _meme)
    _trader.run()
