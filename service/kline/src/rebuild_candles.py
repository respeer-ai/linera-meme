import argparse

from db import Db


def main():
    parser = argparse.ArgumentParser(description='Rebuild kline candles from persisted transactions')
    parser.add_argument('--database-host', type=str, default='localhost', help='Kline database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Kline database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')
    parser.add_argument('--token-0', required=True, type=str, help='Forward token0 symbol/id')
    parser.add_argument('--token-1', required=True, type=str, help='Forward token1 symbol/id')
    parser.add_argument('--start-at', required=True, type=int, help='Start timestamp in milliseconds')
    parser.add_argument('--end-at', required=True, type=int, help='End timestamp in milliseconds')
    parser.add_argument('--interval', action='append', dest='intervals', help='Specific interval to rebuild; repeatable')

    args = parser.parse_args()
    db = Db(
        args.database_host,
        args.database_port,
        args.database_name,
        args.database_user,
        args.database_password,
        False,
    )
    try:
        results = db.rebuild_pair_candles(
            token_0=args.token_0,
            token_1=args.token_1,
            start_at=args.start_at,
            end_at=args.end_at,
            intervals=args.intervals,
        )
        for key in sorted(results.keys()):
            print(f'{key}={results[key]}')
    finally:
        db.close()


if __name__ == '__main__':
    main()
