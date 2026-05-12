import argparse
import asyncio
import os


from swap import Swap
from meme import Meme
from proxy import Proxy
from wallet import Wallet
from trader import Trader
from db import Db


def require_env(name: str) -> str:
    value = str(os.environ.get(name) or '').strip()
    if value == '':
        raise RuntimeError(f'missing_required_env:{name}')
    return value


async def main():
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-chain-id', type=str, required=True, help='Swap chain id')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--wallet-host', type=str, default='localhost:30081', help='Host of wallet service')
    parser.add_argument('--proxy-host', type=str, default='api.linerameme.fun', help='Host of meme service')
    parser.add_argument('--proxy-chain-id', type=str, required=True, help='Proxy chain id')
    parser.add_argument('--proxy-application-id', type=str, required=True, help='Proxy application id')
    parser.add_argument('--faucet-url', type=str, default='https://faucet.testnet-conway.linera.net', help='Faucet url')
    parser.add_argument('--database-host', type=str, default='localhost', help='Kline database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Kline database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')

    args = parser.parse_args()
    wallet_owner = require_env('WALLET_OWNER')
    wallet_chain = require_env('WALLET_CHAIN')

    _db = Db(args.database_host, args.database_port, args.database_name, args.database_user, args.database_password, False)
    _wallet = Wallet(args.wallet_host, wallet_owner, wallet_chain, args.faucet_url, db=_db)
    _meme = Meme(
        args.proxy_host,
        _wallet,
        query_base_url=f'http://{args.proxy_host}/api/proxy/query',
    )

    _swap = Swap(
        args.swap_host,
        args.swap_chain_id,
        args.swap_application_id,
        _wallet,
        db=_db,
        query_base_url=f'http://{args.swap_host}/api/swap/query',
    )

    _proxy = Proxy(
        args.proxy_host,
        args.proxy_chain_id,
        args.proxy_application_id,
        db=_db,
        query_base_url=f'http://{args.proxy_host}/api/proxy/query',
        mutation_base_url=f'http://{args.proxy_host}/api/proxy/mutation',
    )
    try:
        _trader = Trader(_swap, _wallet, _meme, _proxy, db=_db)
        await _trader.run()
    finally:
        _db.close()

if __name__ == '__main__':
    asyncio.run(main())
