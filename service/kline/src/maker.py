import argparse


from swap import Swap
from meme import Meme
from wallet import Wallet
from trader import Trader


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--wallet-host', type=str, default='localhost:30081', help='Host of wallet service')
    parser.add_argument('--wallet-owner', type=str, default='', help='Owner of wallet')
    parser.add_argument('--wallet-chain', type=str, default='', help='Chain of wallet')
    parser.add_argument('--proxy-host', type=str, default='api.linerameme.fun', help='Host of meme service')
    parser.add_argument('--faucet-url', type=str, default='https://faucet.testnet-conway.linera.net', help='Faucet url')

    args = parser.parse_args()

    _wallet = Wallet(args.wallet_host, args.wallet_owner, args.wallet_chain, args.faucet_url)
    _meme = Meme(args.proxy_host, _wallet)

    _swap = Swap(args.swap_host, args.swap_application_id, _wallet)
    _swap.get_swap_chain()
    _swap.get_swap_application()

    _trader = Trader(_swap, _wallet, _meme)
    _trader.run()
