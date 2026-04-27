import asyncio
import threading
import time
import traceback


class MakerRuntime:
    def __init__(self, now_ms, config):
        self._now_ms = now_ms
        self._config = config
        self._thread = None
        self._stop_event = None
        self._lock = threading.Lock()
        self._trader = None
        self._status = {
            'enabled': False,
            'running': False,
            'started_at_ms': None,
            'last_iteration_started_at_ms': None,
            'last_iteration_finished_at_ms': None,
            'last_sleep_seconds': None,
            'last_trade_duration_ms': None,
            'last_error': None,
            'last_error_at_ms': None,
            'consecutive_failures': 0,
            'iterations': 0,
        }

    def configured(self) -> bool:
        required_values = (
            self._config.get('swap_host'),
            self._config.get('swap_chain_id'),
            self._config.get('swap_application_id'),
            self._config.get('wallet_host'),
            self._config.get('wallet_owner'),
            self._config.get('wallet_chain'),
            self._config.get('proxy_host'),
            self._config.get('proxy_chain_id'),
            self._config.get('proxy_application_id'),
            self._config.get('database_host'),
            self._config.get('database_port'),
            self._config.get('database_user'),
            self._config.get('database_password'),
            self._config.get('database_name'),
        )
        return all(value not in (None, '') for value in required_values)

    def start(self):
        with self._lock:
            self._status['enabled'] = self.configured()
            if self._status['enabled'] is not True:
                return
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run_in_thread,
                name='maker-runtime',
                daemon=True,
            )
            self._thread.start()

    def stop(self, timeout_seconds: float = 10.0):
        thread = None
        stop_event = None
        with self._lock:
            thread = self._thread
            stop_event = self._stop_event
        if stop_event is not None:
            stop_event.set()
        if thread is not None:
            thread.join(timeout=timeout_seconds)
        with self._lock:
            self._thread = None
            self._stop_event = None
            self._trader = None
            self._status['running'] = False

    def status(self) -> dict:
        with self._lock:
            status = dict(self._status)
            status['cycle'] = None if self._trader is None else self._trader.debug_snapshot()
            return status

    def _set_status(self, **fields):
        with self._lock:
            self._status.update(fields)

    def _run_in_thread(self):
        asyncio.run(self._run_async())

    async def _run_async(self):
        from db import Db
        from meme import Meme
        from proxy import Proxy
        from swap import Swap
        from trader import Trader
        from wallet import Wallet

        trader_db = Db(
            self._config['database_host'],
            self._config['database_port'],
            self._config['database_name'],
            self._config['database_user'],
            self._config['database_password'],
            False,
        )
        wallet = Wallet(
            self._config['wallet_host'],
            self._config['wallet_owner'],
            self._config['wallet_chain'],
            self._config['faucet_url'],
            db=trader_db,
        )
        meme = Meme(self._config['proxy_host'], wallet)
        swap = Swap(
            self._config['swap_host'],
            self._config['swap_chain_id'],
            self._config['swap_application_id'],
            wallet,
            db=trader_db,
        )
        proxy = Proxy(
            self._config['proxy_host'],
            self._config['proxy_chain_id'],
            self._config['proxy_application_id'],
            db=trader_db,
        )
        trader = Trader(swap, wallet, meme, proxy, db=trader_db)
        with self._lock:
            self._trader = trader
        self._set_status(
            running=True,
            started_at_ms=self._now_ms(),
            last_error=None,
            last_error_at_ms=None,
            consecutive_failures=0,
        )

        try:
            while self._stop_event is not None and self._stop_event.is_set() is not True:
                iteration_started_at_ms = self._now_ms()
                self._set_status(last_iteration_started_at_ms=iteration_started_at_ms)
                try:
                    timeout = await trader.trade()
                    trade_duration_ms = self._now_ms() - iteration_started_at_ms
                    current_status = self.status()
                    self._set_status(
                        iterations=int(current_status['iterations']) + 1,
                        last_trade_duration_ms=trade_duration_ms,
                        last_iteration_finished_at_ms=self._now_ms(),
                        last_sleep_seconds=float(timeout),
                        last_error=None,
                        last_error_at_ms=None,
                        consecutive_failures=0,
                    )
                    print(f'Trade pools took {trade_duration_ms / 1000:.6f} seconds')
                except Exception as e:
                    current_status = self.status()
                    self._set_status(
                        last_trade_duration_ms=self._now_ms() - iteration_started_at_ms,
                        last_iteration_finished_at_ms=self._now_ms(),
                        last_error=str(e),
                        last_error_at_ms=self._now_ms(),
                        consecutive_failures=int(current_status['consecutive_failures']) + 1,
                        last_sleep_seconds=5.0,
                    )
                    print(f'Trader runtime failed at {time.time()}: ERROR {e}')
                    traceback.print_exc()
                    timeout = 5.0

                await asyncio.sleep(float(timeout))
        finally:
            with self._lock:
                self._trader = None
            self._set_status(running=False)
            trader_db.close()
