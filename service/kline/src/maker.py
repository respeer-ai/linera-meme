import argparse


from swap import Swap
from trader import Trader


def run_maker(swap, trader):
    print('Run maker')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Market Maker')

    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--wallet-host', type=str, default='localhost:8080', help='Host of wallet service')

    args = parser.parse_args()

    _swap = Swap(args.swap_host, args.swap_application_id)
    _swap.get_swap_chain()
    _swap.get_swap_application()

    _trader = Trader(args.wallet_host)

    while True:
        run_maker(_swap, _trader)
        time.sleep(10)
