import os
import re
import time

from storage.mysql.debug_traces_query_repo import DebugTracesQueryRepository
from storage.mysql.maker_events_query_repo import MakerEventsQueryRepository
from storage.mysql.pool_catalog_query_repo import PoolCatalogQueryRepository
from storage.mysql.transaction_watermarks_query_repo import TransactionWatermarksQueryRepository


class MakerApiRuntime:
    def __init__(self, db, config: dict, request_client, clock_ms=None):
        self._db = db
        self._config = config
        self._request_client = request_client
        self._clock_ms = clock_ms or self._default_now_ms

    def now_ms(self) -> int:
        return int(self._clock_ms())

    def build_wallet_host(self, index: int) -> str:
        template = str(self._config.get('wallet_host_template') or '').strip()
        if template == '':
            return self.sanitize_wallet_host(f'maker-wallet-service-{index}.maker-wallet-service')

        for placeholder in ('{index}', '${index}', '{{index}}'):
            if placeholder in template:
                return self.sanitize_wallet_host(template.replace(placeholder, str(index)))

        malformed_match = re.match(r'^(.*)\{index(?:\.([^}]+))?\}(.*)$', template)
        if malformed_match is not None:
            prefix, embedded_suffix, trailing_suffix = malformed_match.groups()
            suffix = trailing_suffix
            if embedded_suffix:
                suffix = embedded_suffix if embedded_suffix.startswith(('.', ':', '/')) else f'.{embedded_suffix}'
                suffix += trailing_suffix
            return self.sanitize_wallet_host(f'{prefix}{index}{suffix}')

        try:
            return self.sanitize_wallet_host(template.format(index=index))
        except Exception:
            return self.sanitize_wallet_host(template)

    def sanitize_wallet_host(self, host: str) -> str:
        trimmed = str(host or '').strip().strip('{}')
        if trimmed == '':
            return ''

        labels = []
        for raw_label in trimmed.split('.'):
            label = raw_label.strip().strip('{}')
            if label == '':
                continue
            if len(labels) > 0 and labels[-1] == label:
                continue
            labels.append(label)

        return '.'.join(labels)

    def build_wallet_rpc_url(self, index: int) -> str:
        return f'http://{self.build_wallet_host(index)}:{self._config["wallet_rpc_port"]}'

    def build_wallet_metrics_url(self, index: int) -> str:
        return f'http://{self.build_wallet_host(index)}:{self._config["wallet_metrics_port"]}/metrics'

    def load_wallet_descriptor(self, index: int):
        path = os.path.join(
            self._config['shared_app_data_dir'],
            f'MAKER_WALLET_CHAIN_OWNER.{index}',
        )
        descriptor = {
            'index': index,
            'state_path': path,
            'state_file_exists': os.path.exists(path),
            'chain_id': None,
            'owner': None,
        }
        if descriptor['state_file_exists'] is not True:
            return descriptor

        with open(path, 'r', encoding='utf-8') as file_handle:
            lines = [line.strip() for line in file_handle.readlines() if line.strip()]

        if len(lines) >= 1:
            descriptor['chain_id'] = lines[0]
        if len(lines) >= 2:
            descriptor['owner'] = lines[1]
        return descriptor

    def parse_prometheus_metrics(self, body: str):
        metrics = {}
        for raw_line in body.splitlines():
            line = raw_line.strip()
            if line == '' or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            raw_name = parts[0]
            metric_name = raw_name.split('{', 1)[0]

            try:
                metrics[metric_name] = float(parts[-1])
            except ValueError:
                continue
        return metrics

    def summarize_wallet_metrics(self, metrics: dict):
        resident_memory_bytes = metrics.get('process_resident_memory_bytes')
        virtual_memory_bytes = metrics.get('process_virtual_memory_bytes')
        memory_limit_bytes = int(self._config.get('wallet_memory_limit_bytes') or 0)
        resident_memory_ratio = None
        memory_high = False

        if resident_memory_bytes is not None and memory_limit_bytes > 0:
            resident_memory_ratio = resident_memory_bytes / memory_limit_bytes
            memory_high = resident_memory_ratio >= 0.85

        selected_metrics = {}
        for key in sorted(metrics.keys()):
            lowered = key.lower()
            if (
                lowered.startswith('process_')
                or 'memory' in lowered
                or 'listener' in lowered
                or 'queue' in lowered
                or 'pending' in lowered
                or 'sync' in lowered
                or 'certificate' in lowered
                or 'inbox' in lowered
                or 'outbox' in lowered
            ):
                selected_metrics[key] = metrics[key]

        return {
            'metric_count': len(metrics),
            'resident_memory_bytes': resident_memory_bytes,
            'resident_memory_mib': None if resident_memory_bytes is None else round(resident_memory_bytes / 1024 / 1024, 2),
            'virtual_memory_bytes': virtual_memory_bytes,
            'virtual_memory_mib': None if virtual_memory_bytes is None else round(virtual_memory_bytes / 1024 / 1024, 2),
            'open_fds': metrics.get('process_open_fds'),
            'start_time_seconds': metrics.get('process_start_time_seconds'),
            'wallet_memory_limit_bytes': memory_limit_bytes if memory_limit_bytes > 0 else None,
            'resident_memory_ratio': None if resident_memory_ratio is None else round(resident_memory_ratio, 4),
            'memory_high': memory_high,
            'selected_metrics': selected_metrics,
        }

    async def fetch_wallet_metrics(self, index: int):
        url = self.build_wallet_metrics_url(index)
        try:
            response = await self._request_client.get(url=url, timeout=(2, 5))
            if response.ok is not True:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'metrics_url': url,
                }

            metrics = self.parse_prometheus_metrics(response.text)
            return {
                'reachable': True,
                'status_code': response.status_code,
                'metrics_url': url,
                'summary': self.summarize_wallet_metrics(metrics),
            }
        except Exception as exc:
            return {
                'reachable': False,
                'status_code': None,
                'error': str(exc),
                'metrics_url': url,
            }

    async def fetch_wallet_balances(self, index: int, descriptor: dict):
        if descriptor.get('chain_id') is None or descriptor.get('owner') is None:
            return {
                'reachable': False,
                'error': 'wallet chain/owner metadata is unavailable',
            }

        chain_id = descriptor['chain_id']
        owner = descriptor['owner']
        payload = {
            'query': f'query {{\n balances(chainOwners:[{{chainId: "{chain_id}", owners: ["{owner}"]}}]) \n}}'
        }
        url = self.build_wallet_rpc_url(index)

        try:
            response, payload_json = await self.post_wallet_query(index, payload, timeout=(3, 10))
            if response.ok is not True:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'wallet_url': url,
                }
            if 'errors' in payload_json:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': payload_json['errors'],
                    'wallet_url': url,
                }

            balances = payload_json.get('data', {}).get('balances', {})
            chain_balances = balances.get(chain_id, {})
            owner_balances = chain_balances.get('ownerBalances', {})
            chain_balance = float(chain_balances.get('chainBalance', 0))
            owner_balance = float(owner_balances.get(owner, 0))
            return {
                'reachable': True,
                'status_code': response.status_code,
                'wallet_url': url,
                'chain_id': chain_id,
                'owner': owner,
                'chain_balance': chain_balance,
                'owner_balance': owner_balance,
                'total_balance': chain_balance + owner_balance,
            }
        except Exception as exc:
            return {
                'reachable': False,
                'status_code': None,
                'error': str(exc),
                'wallet_url': url,
            }

    async def post_wallet_query(self, index: int, payload: dict, timeout=(3, 10)):
        response = await self._request_client.post(url=self.build_wallet_rpc_url(index), json=payload, timeout=timeout)
        payload_json = response.json() if response.text else {}
        return response, payload_json

    async def fetch_wallet_block(self, index: int, chain_id: str, block_hash: str):
        payload = {
            'query': (
                'query {'
                f' block(chainId: "{chain_id}", hash: "{block_hash}") {{'
                '  hash'
                '  status'
                '  block {'
                '   header {'
                '    chainId'
                '    height'
                '    timestamp'
                '    previousBlockHash'
                '   }'
                '   body {'
                '    messages {'
                '     destination'
                '     authenticatedSigner'
                '     kind'
                '     grant'
                '     message'
                '    }'
                '   }'
                '  }'
                ' }'
                '}'
            )
        }
        url = self.build_wallet_rpc_url(index)

        try:
            response, payload_json = await self.post_wallet_query(index, payload, timeout=(3, 10))
            if response.ok is not True:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'wallet_url': url,
                }
            if 'errors' in payload_json:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': payload_json['errors'],
                    'wallet_url': url,
                }
            return {
                'reachable': True,
                'status_code': response.status_code,
                'wallet_url': url,
                'block': payload_json.get('data', {}).get('block'),
            }
        except Exception as exc:
            return {
                'reachable': False,
                'status_code': None,
                'error': str(exc),
                'wallet_url': url,
            }

    async def fetch_wallet_pending_messages(self, index: int, chain_id: str):
        payload = {
            'query': (
                'query {'
                f' pendingMessages(chainId: "{chain_id}") {{'
                '  action'
                '  origin'
                '  bundle {'
                '   certificateHash'
                '   height'
                '   timestamp'
                '   transactionIndex'
                '  }'
                ' }'
                '}'
            )
        }
        url = self.build_wallet_rpc_url(index)

        try:
            response, payload_json = await self.post_wallet_query(index, payload, timeout=(3, 10))
            if response.ok is not True:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': f'HTTP {response.status_code}',
                    'wallet_url': url,
                }
            if 'errors' in payload_json:
                return {
                    'reachable': False,
                    'status_code': response.status_code,
                    'error': payload_json['errors'],
                    'wallet_url': url,
                }
            return {
                'reachable': True,
                'status_code': response.status_code,
                'wallet_url': url,
                'pending_messages': payload_json.get('data', {}).get('pendingMessages'),
            }
        except Exception as exc:
            return {
                'reachable': False,
                'status_code': None,
                'error': str(exc),
                'wallet_url': url,
            }

    def build_wallet_health(self, metrics_result, balances_result):
        if metrics_result is not None and metrics_result.get('reachable') is not True:
            return 'wallet_metrics_unreachable'

        if balances_result is not None:
            if balances_result.get('reachable') is not True:
                return 'wallet_balance_unreachable'
            if balances_result.get('total_balance', 0) < 0.001:
                return 'wallet_low_gas'

        if metrics_result is not None:
            summary = metrics_result.get('summary', {})
            if summary.get('memory_high') is True:
                return 'wallet_memory_high'

        return 'ok'

    async def build_wallet_snapshot(self, index: int, include_metrics: bool, include_balances: bool):
        descriptor = self.load_wallet_descriptor(index)
        metrics_result = await self.fetch_wallet_metrics(index) if include_metrics else None
        balances_result = await self.fetch_wallet_balances(index, descriptor) if include_balances else None

        return {
            'index': index,
            'rpc_url': self.build_wallet_rpc_url(index),
            'metrics_url': self.build_wallet_metrics_url(index),
            'chain_id': descriptor.get('chain_id'),
            'owner': descriptor.get('owner'),
            'state_path': descriptor.get('state_path'),
            'state_file_exists': descriptor.get('state_file_exists'),
            'health': self.build_wallet_health(metrics_result, balances_result),
            'metrics': metrics_result,
            'balances': balances_result,
        }

    async def build_wallet_index(self, include_metrics: bool, include_balances: bool):
        wallets = []
        for index in range(int(self._config['maker_replicas'])):
            wallets.append(await self.build_wallet_snapshot(
                index=index,
                include_metrics=include_metrics,
                include_balances=include_balances,
            ))
        return wallets

    def group_latest_by(self, rows: list, key_builder):
        latest = {}
        for row in rows:
            key = key_builder(row)
            if key is None:
                continue
            created_at = int(row.get('created_at') or 0)
            current = latest.get(key)
            if current is None or created_at >= int(current.get('created_at') or 0):
                latest[key] = row
        return latest

    def debug_traces_query_repository(self):
        return DebugTracesQueryRepository(self._db)

    def maker_events_query_repository(self):
        return MakerEventsQueryRepository(self._db)

    def pool_catalog_query_repository(self):
        return PoolCatalogQueryRepository(self._db)

    def transaction_watermarks_query_repository(self):
        return TransactionWatermarksQueryRepository(self._db)

    def get_maker_events(self, token0: str, token1: str, start_at: int, end_at: int):
        return self.maker_events_query_repository().get_maker_events(
            token_0=token0,
            token_1=token1,
            start_at=start_at,
            end_at=end_at,
        )

    def get_combined_maker_events(self, start_at: int, end_at: int):
        return self.maker_events_query_repository().get_maker_events(
            token_0=None,
            token_1=None,
            start_at=start_at,
            end_at=end_at,
        )

    def get_maker_events_information(self, token0: str | None, token1: str | None):
        return self.maker_events_query_repository().get_maker_events_information(
            token_0=token0,
            token_1=token1,
        )

    async def get_debug_wallets(self, include_metrics: bool, include_balances: bool):
        return {
            'wallets': await self.build_wallet_index(
                include_metrics=include_metrics,
                include_balances=include_balances,
            ),
        }

    async def get_debug_wallet_metrics(self, index: int):
        self.validate_wallet_index(index)
        descriptor = self.load_wallet_descriptor(index)
        return {
            'index': index,
            'chain_id': descriptor.get('chain_id'),
            'owner': descriptor.get('owner'),
            'metrics': await self.fetch_wallet_metrics(index),
        }

    async def get_debug_wallet_balances(self, index: int):
        self.validate_wallet_index(index)
        descriptor = self.load_wallet_descriptor(index)
        return {
            'index': index,
            'balances': await self.fetch_wallet_balances(index, descriptor),
        }

    async def get_debug_wallet_block(self, index: int, chain_id: str, block_hash: str):
        self.validate_wallet_index(index)
        return {
            'index': index,
            'chain_id': chain_id,
            'block_hash': block_hash,
            'result': await self.fetch_wallet_block(index=index, chain_id=chain_id, block_hash=block_hash),
        }

    async def get_debug_wallet_pending_messages(self, index: int, chain_id: str):
        self.validate_wallet_index(index)
        return {
            'index': index,
            'chain_id': chain_id,
            'result': await self.fetch_wallet_pending_messages(index=index, chain_id=chain_id),
        }

    def get_debug_traces(
        self,
        source: str | None,
        component: str | None,
        operation: str | None,
        owner: str | None,
        pool_application: str | None,
        pool_id: int | None,
        start_at: int | None,
        end_at: int | None,
        limit: int,
        include_payloads: bool,
    ):
        self.require_db()
        if limit <= 0:
            raise ValueError('limit must be positive')

        return {
            'traces': self.debug_traces_query_repository().get_debug_traces(
                source=source,
                component=component,
                operation=operation,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
                include_payloads=include_payloads,
            ),
        }

    async def get_debug_pools_stall(
        self,
        pool_id: int | None,
        owner: str | None,
        lookback_minutes: int,
        stall_seconds: int,
        include_wallets: bool,
    ):
        self.require_db()
        if lookback_minutes <= 0:
            raise ValueError('lookback_minutes must be positive')
        if stall_seconds <= 0:
            raise ValueError('stall_seconds must be positive')

        current_ms = self.now_ms()
        start_at = current_ms - lookback_minutes * 60 * 1000
        pool_catalog = self.pool_catalog_query_repository().get_pool_catalog()
        if pool_id is not None:
            pool_catalog = [row for row in pool_catalog if int(row['pool_id']) == int(pool_id)]

        latest_watermarks = self.transaction_watermarks_query_repository().get_latest_transaction_watermarks()
        maker_events = self.maker_events_query_repository().get_maker_events(
            token_0=None,
            token_1=None,
            start_at=start_at,
            end_at=current_ms,
        )
        if pool_id is not None:
            maker_events = [row for row in maker_events if int(row['pool_id']) == int(pool_id)]

        traces = self.debug_traces_query_repository().get_debug_traces(
            source='maker',
            component='swap',
            operation='swap',
            owner=owner,
            pool_id=pool_id,
            start_at=start_at,
            end_at=current_ms,
            limit=1000,
        )

        latest_events_by_pool = self.group_latest_by(
            maker_events,
            key_builder=lambda row: int(row['pool_id']) if row.get('pool_id') is not None else None,
        )
        latest_traces_by_pool = self.group_latest_by(
            traces,
            key_builder=lambda row: (row.get('pool_application'), int(row['pool_id'])) if row.get('pool_application') is not None and row.get('pool_id') is not None else None,
        )

        wallet_snapshots = await self.build_wallet_index(
            include_metrics=include_wallets,
            include_balances=include_wallets,
        ) if include_wallets else []
        wallet_by_owner = {
            row['owner']: row
            for row in wallet_snapshots
            if row.get('owner') is not None
        }

        stalled_pools = []
        for pool in pool_catalog:
            pool_application = pool['pool_application']
            pool_key_parts = pool_application.split(':', 1)
            if len(pool_key_parts) != 2:
                continue

            latest_tx = latest_watermarks.get((pool['pool_id'], pool_key_parts[0], pool_key_parts[1]))
            latest_event = latest_events_by_pool.get(pool['pool_id'])
            latest_trace = latest_traces_by_pool.get((pool_application, pool['pool_id']))
            latest_trace_owner = latest_trace.get('owner') if latest_trace is not None else None
            wallet_snapshot = wallet_by_owner.get(latest_trace_owner)

            latest_tx_created_at = None if latest_tx is None else int(latest_tx[0])
            latest_event_created_at = None if latest_event is None else int(latest_event['created_at'])
            latest_trace_created_at = None if latest_trace is None else int(latest_trace['created_at'])
            latest_upstream_created_at = max(
                [value for value in [latest_event_created_at, latest_trace_created_at] if value is not None],
                default=None,
            )

            suspected_stage = 'unknown'
            lag_seconds = None
            if latest_upstream_created_at is None:
                suspected_stage = 'maker_idle'
                if latest_tx_created_at is not None:
                    lag_seconds = round((current_ms - latest_tx_created_at) / 1000, 3)
            else:
                baseline_created_at = latest_tx_created_at if latest_tx_created_at is not None else 0
                lag_seconds = round((latest_upstream_created_at - baseline_created_at) / 1000, 3)
                if latest_trace is not None and latest_tx_created_at is not None and latest_trace_created_at <= latest_tx_created_at + stall_seconds * 1000:
                    suspected_stage = 'settled'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_metrics_unreachable':
                    suspected_stage = 'wallet_metrics_unreachable'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_low_gas':
                    suspected_stage = 'wallet_low_gas'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_memory_high':
                    suspected_stage = 'wallet_memory_high'
                else:
                    suspected_stage = 'mutation_accepted_but_not_settled'

            if latest_upstream_created_at is None and latest_tx_created_at is not None:
                should_include = (current_ms - latest_tx_created_at) >= stall_seconds * 1000
            elif latest_upstream_created_at is None:
                should_include = False
            elif latest_tx_created_at is None:
                should_include = True
            else:
                should_include = latest_upstream_created_at > latest_tx_created_at + stall_seconds * 1000

            if should_include is not True:
                continue

            stalled_pools.append({
                'pool_id': pool['pool_id'],
                'pool_application': pool_application,
                'token_0': pool['token_0'],
                'token_1': pool['token_1'],
                'lag_seconds': lag_seconds,
                'suspected_stage': suspected_stage,
                'latest_db_transaction': None if latest_tx is None else {
                    'created_at': latest_tx_created_at,
                    'transaction_id': int(latest_tx[1]),
                    'token_reversed': int(latest_tx[2]),
                },
                'latest_maker_event': latest_event,
                'latest_wallet_trace': latest_trace,
                'wallet': wallet_snapshot,
            })

        stalled_pools.sort(
            key=lambda row: (
                -(row['lag_seconds'] or 0),
                row['pool_id'],
            )
        )

        return {
            'generated_at': current_ms,
            'lookback_minutes': lookback_minutes,
            'stall_seconds': stall_seconds,
            'stalled_pools': stalled_pools,
            'wallets': wallet_snapshots if include_wallets else None,
        }

    async def get_debug_health(self):
        self.require_db()
        wallets = await self.build_wallet_index(include_metrics=False, include_balances=False)
        return {
            'status': 'ok',
            'generated_at': self.now_ms(),
            'maker_replicas': int(self._config['maker_replicas']),
            'wallet_state_files_found': len([row for row in wallets if row['state_file_exists'] is True]),
            'wallets': wallets,
        }

    def close(self):
        if self._db is not None:
            self._db.close()

    def require_db(self):
        if self._db is None:
            raise RuntimeError('Db client is not initialized')

    def validate_wallet_index(self, index: int):
        if index < 0 or index >= int(self._config['maker_replicas']):
            raise ValueError('wallet index out of range')

    @staticmethod
    def _default_now_ms():
        return int(time.time() * 1000)
