from decimal import Decimal
import warnings

from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository
from storage.mysql.pool_metadata_projection_resolver import PoolMetadataProjectionResolver
from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from storage.mysql.settled_product_transaction_adapter import SettledProductTransactionAdapter


class SettledLiquidityProjectionRepository:
    def __init__(self, db, *, transaction_adapter=None, metadata_resolver=None):
        self.db = db
        self.transaction_adapter = transaction_adapter or SettledProductTransactionAdapter()
        self.metadata_resolver = (
            metadata_resolver
            or PoolMetadataProjectionResolver(
                pool_catalog_projection_repository=PoolCatalogProjectionRepository(db),
                pool_state_projection_repository=PoolStateProjectionRepository(db),
            )
        )

    def get_positions(
        self,
        *,
        owner: str,
        status: str,
    ) -> list[dict] | None:
        normalized_status = (status or 'active').lower()
        if normalized_status not in {'active', 'closed', 'all'}:
            raise ValueError('Invalid positions status')
        rows = self._load_liquidity_rows(owner=owner, position_liquidity_only=True)
        if rows is None:
            return None
        rows = self._recorded_position_rows(rows)
        aggregated = self._aggregate_positions(rows=rows, owner=owner, normalized_status=normalized_status)
        return aggregated

    def get_position_liquidity_history(
        self,
        *,
        owner: str,
        pool_application: str,
        pool_id: int | None,
    ) -> list[dict] | None:
        rows = self._load_liquidity_rows(
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            position_liquidity_only=True,
        )
        if rows is None:
            return None
        return [self._build_history_row(row) for row in self._recorded_position_rows(rows)]

    def list_active_position_owners_for_pool(
        self,
        *,
        pool_application: str,
    ) -> list[str]:
        rows = self._load_liquidity_rows(
            owner=None,
            pool_application=pool_application,
            position_liquidity_only=True,
        )
        if rows is None:
            return []
        liquidity_by_owner: dict[str, Decimal] = {}
        for row in self._recorded_position_rows(rows):
            owner = self.transaction_adapter.public_owner_from_settled_owner(row.get('owner'))
            if owner in (None, ''):
                continue
            delta = self._display_decimal(Decimal(str(row['liquidity_delta'])))
            current = liquidity_by_owner.get(owner, Decimal('0'))
            if row['change_type'] == 'add_liquidity':
                current += delta
            elif row['change_type'] == 'remove_liquidity':
                current -= delta
            liquidity_by_owner[owner] = current
        return sorted(
            owner
            for owner, liquidity in liquidity_by_owner.items()
            if liquidity > Decimal('0.000000000001')
        )

    def get_owner_candidate_histories(
        self,
        *,
        owner: str,
    ) -> list[dict] | None:
        position_rows = self._load_liquidity_rows(owner=owner, position_liquidity_only=True)
        virtual_rows = self._load_virtual_initial_liquidity_rows(owner=owner)
        if position_rows is None or virtual_rows is None:
            return None
        grouped: dict[tuple[str, int], dict] = {}
        for row in position_rows + virtual_rows:
            key = (str(row['pool_application']), int(row['pool_id']))
            current = grouped.get(key)
            if current is None:
                current = {
                    'pool_application': row['pool_application'],
                    'pool_id': int(row['pool_id']),
                    'token_0': row['token_0'],
                    'token_1': row['token_1'],
                    'owner': owner,
                    'opened_at': None,
                    'updated_at': None,
                    'add_tx_count': 0,
                    'virtual_initial_amount0': None,
                    'virtual_initial_amount1': None,
                    'virtual_initial_liquidity': None,
                    'protocol_fee_receiver_account': row.get('protocol_fee_receiver_account'),
                }
                grouped[key] = current
            event_time_ms = int(row['event_time_ms']) if row['event_time_ms'] is not None else None
            if row['change_type'] == 'add_liquidity':
                current['add_tx_count'] += 1
                if current['opened_at'] is None or (event_time_ms is not None and event_time_ms < current['opened_at']):
                    current['opened_at'] = event_time_ms
                if row.get('liquidity_semantics') == 'virtual_initial_liquidity':
                    current['virtual_initial_amount0'] = self._display_decimal(Decimal(str(row['amount_0_delta'])))
                    current['virtual_initial_amount1'] = self._display_decimal(Decimal(str(row['amount_1_delta'])))
                    current['virtual_initial_liquidity'] = self._display_decimal(Decimal(str(row['liquidity_delta'])))
                    current['protocol_fee_receiver_account'] = row.get('protocol_fee_receiver_account')
            if event_time_ms is not None and (current['updated_at'] is None or event_time_ms > current['updated_at']):
                current['updated_at'] = event_time_ms
        return list(grouped.values())

    def _load_virtual_initial_liquidity_rows(self, *, owner: str) -> list[dict] | None:
        rows = self._load_liquidity_rows(
            owner=None,
            liquidity_semantics='virtual_initial_liquidity',
        )
        if rows is None:
            return None
        matched = []
        for row in rows:
            protocol_fee_receiver_account = self._protocol_fee_receiver_account(row)
            creator_account = row.get('creator_account')
            if protocol_fee_receiver_account != owner and creator_account != owner:
                continue
            enriched = dict(row)
            enriched['owner'] = self.transaction_adapter.settled_owner_from_public_owner(owner)
            enriched['protocol_fee_receiver_account'] = protocol_fee_receiver_account or creator_account
            matched.append(enriched)
        return matched

    def get_pool_liquidity_history(
        self,
        *,
        pool_application: str,
        pool_id: int | None,
    ) -> list[dict] | None:
        rows = self._load_liquidity_rows(
            owner=None,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if rows is None:
            return None
        return [self._build_history_row(row) for row in rows]

    def _load_liquidity_rows(
        self,
        *,
        owner: str | None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        position_liquidity_only: bool = False,
        liquidity_semantics: str | None = None,
    ) -> list[dict] | None:
        if not hasattr(self.db, 'ensure_fresh_read_connection'):
            return None
        if not hasattr(self.db, 'cursor_dict'):
            return None
        cursor = self.db.fresh_cursor(dictionary=True)
        where_clauses = []
        params: list[object] = []
        if owner is not None:
            where_clauses.append('slc.owner = %s')
            params.append(self.transaction_adapter.settled_owner_from_public_owner(owner))
        if position_liquidity_only:
            where_clauses.append(self._position_liquidity_condition('slc'))
        if liquidity_semantics is not None:
            where_clauses.append('slc.liquidity_semantics = %s')
            params.append(liquidity_semantics)
        if pool_application is not None:
            where_clauses.append(self._pool_application_condition('slc'))
            params.append(pool_application)
        if pool_id is not None:
            metadata_by_pool_application = self.metadata_resolver.metadata_by_pool_application()
            pool_applications = [
                pool_application_key
                for pool_application_key, metadata in metadata_by_pool_application.items()
                if int(metadata.get('pool_id') or 0) == int(pool_id)
            ]
            if not pool_applications:
                return []
            placeholders = ', '.join(['%s'] * len(pool_applications))
            where_clauses.append(f"{self._pool_application_expression('slc')} IN ({placeholders})")
            params.extend(pool_applications)
        try:
            cursor.execute(
                f'''
                SELECT
                    {self._pool_application_expression('slc')} AS pool_application,
                    slc.owner,
                    slc.transaction_id,
                    slc.change_type,
                    slc.liquidity_delta,
                    slc.is_position_liquidity,
                    slc.liquidity_semantics,
                    slc.amount_0_delta,
                    slc.amount_1_delta,
                    slc.event_time_ms
                FROM settled_liquidity_changes slc
                {'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''}
                ORDER BY slc.event_time_ms ASC, slc.transaction_index ASC, slc.settled_liquidity_change_id ASC
                ''',
                tuple(params),
            )
            rows = list(cursor.fetchall() or [])
            return self._attach_pool_metadata(rows)
        except Exception as exc:
            error_message = str(exc)
            if len(error_message) > 500:
                error_message = error_message[:497] + '...'
            warnings.warn(
                f'SettledLiquidityProjectionRepository failed to load liquidity rows: {error_message}',
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        finally:
            cursor.close()

    def _recorded_position_rows(self, rows: list[dict]) -> list[dict]:
        current_by_key: dict[tuple[str, str, int], Decimal] = {}
        recorded_rows = []
        for row in rows:
            owner = str(row.get('owner') or '')
            key = (owner, str(row.get('pool_application') or ''), int(row.get('pool_id') or 0))
            current = current_by_key.get(key, Decimal('0'))
            delta = self._display_decimal(Decimal(str(row['liquidity_delta'])))
            if row['change_type'] == 'add_liquidity':
                current_by_key[key] = current + delta
                recorded_rows.append(row)
                continue
            if row['change_type'] == 'remove_liquidity':
                if current <= Decimal('0') or delta - current > Decimal('0.000000000001'):
                    continue
                next_current = current - delta
                current_by_key[key] = next_current if next_current > Decimal('0.000000000001') else Decimal('0')
                recorded_rows.append(row)
                continue
            recorded_rows.append(row)
        return recorded_rows

    def _aggregate_positions(
        self,
        *,
        rows: list[dict],
        owner: str,
        normalized_status: str,
    ) -> list[dict]:
        grouped: dict[tuple[str, int], dict[str, object]] = {}
        for row in rows:
            key = (str(row['pool_application']), int(row['pool_id']))
            current = grouped.get(key)
            if current is None:
                current = {
                    'pool_application': row['pool_application'],
                    'pool_id': int(row['pool_id']),
                    'token_0': row['token_0'],
                    'token_1': row['token_1'],
                    'owner': owner,
                    'added_liquidity': Decimal('0'),
                    'removed_liquidity': Decimal('0'),
                    'add_tx_count': 0,
                    'remove_tx_count': 0,
                    'opened_at': None,
                    'updated_at': None,
                }
                grouped[key] = current
            liquidity_delta = self._display_decimal(Decimal(str(row['liquidity_delta'])))
            event_time_ms = int(row['event_time_ms']) if row['event_time_ms'] is not None else None
            if row['change_type'] == 'add_liquidity':
                current['added_liquidity'] += liquidity_delta
                current['add_tx_count'] += 1
                if current['opened_at'] is None or (event_time_ms is not None and event_time_ms < current['opened_at']):
                    current['opened_at'] = event_time_ms
            elif row['change_type'] == 'remove_liquidity':
                current['removed_liquidity'] += liquidity_delta
                current['remove_tx_count'] += 1
            if event_time_ms is not None:
                if current['updated_at'] is None or event_time_ms > current['updated_at']:
                    current['updated_at'] = event_time_ms
        positions = []
        for current in grouped.values():
            added_liquidity = current['added_liquidity']
            removed_liquidity = current['removed_liquidity']
            net_liquidity = added_liquidity - removed_liquidity
            if net_liquidity < Decimal('0') or abs(net_liquidity) < Decimal('0.000000000001'):
                net_liquidity = Decimal('0')
            position_status = 'active' if net_liquidity > 0 else 'closed'
            if normalized_status != 'all' and position_status != normalized_status:
                continue
            updated_at = current['updated_at']
            positions.append({
                'pool_application': current['pool_application'],
                'pool_id': int(current['pool_id']),
                'token_0': current['token_0'],
                'token_1': current['token_1'],
                'owner': owner,
                'status': position_status,
                'current_liquidity': self._serialize_decimal(net_liquidity),
                'added_liquidity': self._serialize_decimal(added_liquidity),
                'removed_liquidity': self._serialize_decimal(removed_liquidity),
                'add_tx_count': int(current['add_tx_count']),
                'remove_tx_count': int(current['remove_tx_count']),
                'opened_at': current['opened_at'],
                'updated_at': updated_at,
                'closed_at': updated_at if position_status == 'closed' and updated_at is not None else None,
            })
        positions.sort(
            key=lambda row: (
                -(row['closed_at'] if normalized_status == 'closed' else row['updated_at'] or 0),
                row['pool_id'],
            ),
        )
        return positions

    def _build_history_row(self, row: dict) -> dict:
        serialized_row = dict(row)
        serialized_row['amount_0_delta'] = self._serialize_decimal(Decimal(str(row['amount_0_delta'])))
        serialized_row['amount_1_delta'] = self._serialize_decimal(Decimal(str(row['amount_1_delta'])))
        serialized_row['liquidity_delta'] = self._serialize_decimal(Decimal(str(row['liquidity_delta'])))
        return self.transaction_adapter.build_liquidity_history_row(serialized_row)

    def _attach_pool_metadata(self, rows: list[dict]) -> list[dict]:
        metadata_by_pool_application = self.metadata_resolver.metadata_by_pool_application()
        enriched = []
        for row in rows:
            pool_application = str(row['pool_application'])
            metadata = metadata_by_pool_application.get(pool_application) or {}
            if metadata.get('pool_id') is None:
                continue
            enriched_row = dict(row)
            enriched_row['pool_id'] = int(metadata['pool_id'])
            enriched_row['token_0'] = metadata.get('token_0')
            enriched_row['token_1'] = metadata.get('token_1')
            enriched_row['creator_account'] = metadata.get('creator_account')
            enriched_row['fee_to_account_latest_known'] = metadata.get('fee_to_account_latest_known')
            enriched.append(enriched_row)
        return enriched

    def _protocol_fee_receiver_account(self, row: dict) -> str | None:
        value = row.get('fee_to_account_latest_known') or row.get('creator_account')
        if value in (None, ''):
            return None
        return str(value)

    def _pool_application_expression(self, alias: str) -> str:
        return f"{alias}.pool_application_id"

    def _pool_application_condition(self, alias: str) -> str:
        return f"{self._pool_application_expression(alias)} = %s"

    def _position_liquidity_condition(self, alias: str) -> str:
        return f"{alias}.is_position_liquidity = TRUE"

    def _serialize_decimal(self, value: Decimal) -> str:
        normalized = format(value.normalize(), 'f')
        if '.' in normalized:
            normalized = normalized.rstrip('0').rstrip('.')
        if normalized in {'', '-0'}:
            return '0'
        return normalized

    def _display_decimal(self, value: Decimal) -> Decimal:
        return value / SettledProductTransactionAdapter.DISPLAY_AMOUNT_SCALE
