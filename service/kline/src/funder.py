import argparse


from swap import Swap
from wallet import Wallet
from trader import Trader
from proxy import Proxy
from feeder import Feeder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--proxy-host', type=str, default='api.linerameme.fun', help='Host of proxy service')
    parser.add_argument('--proxy-application-id', type=str, default='', help='Proxy application id')
    parser.add_argument('--wallet-host', type=str, default='localhost:30081', help='Host of wallet service')
    parser.add_argument('--wallet-owner', type=str, default='', help='Owner of wallet')
    parser.add_argument('--wallet-chain', type=str, default='', help='Chain of wallet')
    parser.add_argument('--faucet-url', type=str, default='https://faucet.testnet-babbage.linera.net', help='Faucet url')

    args = parser.parse_args()

    _wallet = Wallet(args.wallet_host, args.wallet_owner, args.wallet_chain, args.faucet_url)

    _swap = Swap(args.swap_host, args.swap_application_id, _wallet)
    _swap.get_swap_chain()
    _swap.get_swap_application()

    _proxy = Proxy(args.proxy_host, args.proxy_application_id, _wallet)
    _proxy.get_proxy_chain()
    _proxy.get_proxy_application()

    _feeder = Feeder(_swap, _proxy, _wallet)
    _feeder.run()
