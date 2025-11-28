import argparse
import asyncio


from swap import Swap
from wallet import Wallet
from proxy import Proxy
from feeder import Feeder, MakerWallet


async def main():
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--proxy-host', type=str, default='api.linerameme.fun', help='Host of proxy service')
    parser.add_argument('--proxy-application-id', type=str, default='', help='Proxy application id')
    parser.add_argument('--maker-wallet-host', type=str, default='maker-wallet-service:8080', help='Host of maker wallet')
    parser.add_argument('--maker-wallet-chain-id', type=str, default='', help='Maker wallet chain ID')
    parser.add_argument('--maker-wallets', type=str, default='', help='Wallets of maker in $CHAIN_ID@$HOST:$PORT', nargs='+')
    parser.add_argument('--wallet-host', type=str, default='localhost:30081', help='Host of wallet service')
    parser.add_argument('--wallet-owner', type=str, default='', help='Owner of wallet')
    parser.add_argument('--wallet-chain', type=str, default='', help='Chain of wallet')
    parser.add_argument('--faucet-url', type=str, default='https://faucet.testnet-conway.linera.net', help='Faucet url')

    args = parser.parse_args()

    _wallet = Wallet(args.wallet_host, args.wallet_owner, args.wallet_chain, args.faucet_url)

    _swap = Swap(args.swap_host, args.swap_application_id, _wallet)
    await _swap.get_swap_chain()
    await _swap.get_swap_application()

    _proxy = Proxy(args.proxy_host, args.proxy_application_id, _wallet)
    await _proxy.get_proxy_chain()
    await _proxy.get_proxy_application()

    maker_wallets = []
    if args.maker_wallet_host and args.maker_wallet_chain_id:
        maker_wallets.append(MakerWallet(args.maker_wallet_host, args.maker_wallet_chain_id))
    for maker_wallet in (args.maker_wallets or []):
        host_chain_id = maker_wallet.strip().split('@')
        if len(host_chain_id) != 2 or not host_chain_id[0] or not host_chain_id[1]:
            print(f'Invalid host chain id: {host_chain_id}')
            continue
        maker_wallets.append(MakerWallet(host_chain_id[0], host_chain_id[1]))

    _feeder = Feeder(_swap, _proxy, maker_wallets, _wallet)
    await _feeder.run()

if __name__ == '__main__':
    asyncio.run(main())
