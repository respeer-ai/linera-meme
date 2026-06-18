#!/usr/bin/env python3
import argparse
import json
import signal
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


NATIVE_TOKEN = None


class E2EError(Exception):
    pass


@dataclass(frozen=True)
class Pool:
    pool_id: int
    token_0: str
    token_1: str | None
    pool_application_chain: str
    pool_application_owner: str
    reserve_0: Decimal
    reserve_1: Decimal

    @property
    def application_id(self) -> str:
        return self.pool_application_owner[2:] if self.pool_application_owner.startswith("0x") else self.pool_application_owner


class ProductWorkflowE2E:
    def __init__(self, args: argparse.Namespace):
        self.user_wallet_url = args.user_wallet_url.rstrip("/")
        self.proxy_wallet_url = args.proxy_wallet_url.rstrip("/")
        self.swap_wallet_url = args.swap_wallet_url.rstrip("/")
        self.query_url = args.query_url.rstrip("/")
        self.kline_url = args.kline_url.rstrip("/")
        self.proxy_chain_id = args.proxy_chain_id
        self.proxy_application_id = args.proxy_application_id
        self.swap_chain_id = args.swap_chain_id
        self.swap_application_id = args.swap_application_id
        self.ams_application_id = args.ams_application_id
        self.blob_gateway_application_id = args.blob_gateway_application_id
        self.timeout_seconds = None if args.timeout_seconds <= 0 else args.timeout_seconds
        self.request_timeout_seconds = args.request_timeout_seconds
        self.poll_seconds = args.poll_seconds
        self.strict_claim = args.strict_claim
        self.run_id = args.run_id or str(int(time.time()))
        self.wallet_path = Path(args.user_wallet_file)
        self.user_chain_override = args.user_chain_id
        self.user_owner_override = args.user_owner

        self.user_chain_id = ""
        self.user_owner = ""
        self.meme_chains: dict[str, str] = {}
        self.pool_chain_id = ""
        self.skipped_inbox_routes: set[tuple[str, str]] = set()
        self.max_inbox_drain_rounds = 5

    def run(self) -> None:
        self.user_chain_id = self.default_chain_id()
        self.user_owner = self.chain_owner(self.user_chain_id)
        print(f"[product-e2e] user chain: {self.user_chain_id}")
        print(f"[product-e2e] user owner: {self.user_owner}")

        before_tokens = self.proxy_meme_tokens()
        token_0 = self.create_meme_and_wait(before_tokens, suffix="A")
        print(f"[product-e2e] meme/native token: {token_0}")

        native_pool = self.wait_for_pool(token_0=token_0, token_1=NATIVE_TOKEN)
        self.wait_for(
            "initial virtual position metrics projection",
            lambda: self.validate_initial_virtual_position_interfaces(native_pool) or True,
        )
        self.run_pool_funds_workflow(native_pool, "meme/native")

        before_tokens = self.proxy_meme_tokens()
        token_1 = self.create_meme_and_wait(before_tokens, suffix="B")
        print(f"[product-e2e] meme/meme token: {token_1}")

        self.create_meme_meme_pool(token_0, token_1)
        meme_meme_pool = self.wait_for_pool(token_0=token_0, token_1=token_1)
        self.run_pool_funds_workflow(meme_meme_pool, "meme/meme")

        self.check_observability(meme_meme_pool)
        print("[product-e2e] completed")

    def run_pool_funds_workflow(self, pool: Pool, label: str) -> None:
        print(f"[product-e2e] {label} pool: {pool.pool_id} {pool.application_id}")

        pool = self.execute_swap_and_wait(pool)
        self.wait_for_virtual_protocol_fee(pool)
        print(f"[product-e2e] {label} swap completed")

        liquidity = self.execute_add_liquidity_and_wait(pool)
        print(f"[product-e2e] {label} add liquidity completed: {liquidity}")

        pool = self.execute_swap_and_wait(pool)
        self.wait_for_actual_position_fee(pool)
        print(f"[product-e2e] {label} post-add swap fee accrual completed")

        self.execute_remove_liquidity_and_wait(pool, liquidity)
        print(f"[product-e2e] {label} remove liquidity completed")

        self.execute_oversupplied_add_liquidity_claim_path(pool)
        self.execute_failed_add_liquidity_claim_path(pool)
        self.check_claim_capability(pool)

    def create_meme_and_wait(self, before_tokens: set[str], *, suffix: str) -> str:
        logo_hash = self.publish_logo_blob()
        ticker = f"E2E{self.run_id[-7:]}{suffix}".upper()
        variables = {
            "memeInstantiationArgument": {
                "meme": {
                    "initialSupply": "21000000",
                    "totalSupply": "21000000",
                    "name": f"Product E2E {self.run_id} {suffix}",
                    "ticker": ticker,
                    "decimals": 6,
                    "metadata": {
                        "logoStoreType": "Blob",
                        "logo": logo_hash,
                        "description": "Product workflow E2E token",
                        "twitter": None,
                        "telegram": None,
                        "discord": None,
                        "website": None,
                        "github": None,
                        "liveStream": None,
                    },
                    "virtualInitialLiquidity": True,
                    "initialLiquidity": {"fungibleAmount": "10499900", "nativeAmount": "8720"},
                },
                "blobGatewayApplicationId": self.blob_gateway_application_id,
                "amsApplicationId": self.ams_application_id,
                "proxyApplicationId": self.proxy_application_id,
                "swapApplicationId": self.swap_application_id,
            },
            "memeParameters": {
                "creator": self.account(self.user_chain_id, self.user_owner),
                "initialLiquidity": {"fungibleAmount": "10499900", "nativeAmount": "8720"},
                "virtualInitialLiquidity": True,
                "swapCreatorChainId": self.swap_chain_id,
                "enableMining": False,
                "miningSupply": None,
            },
        }
        self.application_graphql(
            self.user_wallet_url,
            self.user_chain_id,
            self.proxy_application_id,
            """
            mutation CreateMeme($memeInstantiationArgument: InstantiationArgument!, $memeParameters: MemeParameters!) {
              createMeme(memeInstantiationArgument: $memeInstantiationArgument, memeParameters: $memeParameters)
            }
            """,
            variables,
        )

        def created_token() -> str | None:
            applications = self.proxy_meme_applications()
            new_tokens = sorted(set(applications) - before_tokens)
            if new_tokens:
                token = new_tokens[-1]
                self.meme_chains[token] = applications[token]
                return token
            return None

        return self.wait_for("meme token creation", created_token)

    def create_meme_meme_pool(self, token_0: str, token_1: str) -> None:
        self.application_graphql(
            self.user_wallet_url,
            self.user_chain_id,
            self.swap_application_id,
            """
            mutation CreatePool(
              $token0: ApplicationId!, $token1: ApplicationId,
              $amount0: Amount!, $amount1: Amount!,
              $to: Account
            ) {
              createPool(
                token0: $token0, token1: $token1,
                amount0: $amount0, amount1: $amount1,
                to: $to
              )
            }
            """,
            {
                "token0": token_0,
                "token1": token_1,
                "amount0": "1",
                "amount1": "1",
                "to": self.account(self.user_chain_id, self.user_owner),
            },
        )

    def execute_swap_and_wait(self, pool: Pool) -> Pool:
        before = self.pool_state(pool)
        before_swap_transaction_id = self.latest_transaction_id(pool, self.swap_transaction_types())
        self.execute_swap(pool)

        def changed_pool() -> Pool | None:
            current = self.find_pool(pool.pool_id)
            if (
                current
                and (current.reserve_0 != before.reserve_0 or current.reserve_1 != before.reserve_1)
                and self.latest_transaction_id(pool, self.swap_transaction_types()) > before_swap_transaction_id
            ):
                self.validate_position_interfaces(current)
                return current
            return None

        return self.wait_for("pool reserve and kline transaction change after swap", changed_pool)

    def execute_swap(self, pool: Pool) -> None:
        self.application_graphql(
            self.user_wallet_url,
            self.user_chain_id,
            pool.application_id,
            """
            mutation Swap($amount1In: Amount, $amount0OutMin: Amount, $to: Account) {
              swap(amount1In: $amount1In, amount0OutMin: $amount0OutMin, to: $to)
            }
            """,
            {
                "amount1In": "1",
                "amount0OutMin": "0",
                "to": self.account(self.user_chain_id, self.user_owner),
            },
        )

    def execute_add_liquidity_and_wait(self, pool: Pool) -> Decimal:
        before_contract_liquidity = self.owner_liquidity_amount(pool)
        before_position_liquidity = self.actual_position_liquidity_amount(pool)
        self.execute_add_liquidity(pool)

        def increased_liquidity() -> Decimal | None:
            current_contract_liquidity = self.owner_liquidity_amount(pool)
            current_position_liquidity = self.actual_position_liquidity_amount(pool)
            if (
                current_position_liquidity > before_position_liquidity
                and current_contract_liquidity > before_contract_liquidity
            ):
                self.validate_position_interfaces(pool)
                return current_position_liquidity
            return None

        return self.wait_for("actual position and kline add-liquidity projection", increased_liquidity)

    def execute_add_liquidity(
        self,
        pool: Pool,
        *,
        amount_0_in: str = "1",
        amount_1_in: str = "1",
        amount_0_out_min: str | None = None,
        amount_1_out_min: str | None = None,
    ) -> None:
        self.application_graphql(
            self.user_wallet_url,
            self.user_chain_id,
            pool.application_id,
            """
            mutation AddLiquidity(
              $amount0In: Amount!, $amount1In: Amount!,
              $amount0OutMin: Amount, $amount1OutMin: Amount,
              $to: Account
            ) {
              addLiquidity(
                amount0In: $amount0In, amount1In: $amount1In,
                amount0OutMin: $amount0OutMin, amount1OutMin: $amount1OutMin,
                to: $to
              )
            }
            """,
            {
                "amount0In": amount_0_in,
                "amount1In": amount_1_in,
                "amount0OutMin": amount_0_out_min,
                "amount1OutMin": amount_1_out_min,
                "to": self.account(self.user_chain_id, self.user_owner),
            },
        )

    def execute_remove_liquidity_and_wait(self, pool: Pool, liquidity: Decimal) -> Decimal:
        if liquidity <= 0:
            raise E2EError("remove liquidity cannot run because actual position liquidity is zero")
        remove_amount = Decimal("0.1") if liquidity >= Decimal("0.1") else liquidity
        before_claims = self.claim_balances_by_token(pool)
        before_position_liquidity = self.actual_position_liquidity_amount(pool)

        self.execute_remove_liquidity(pool, str(remove_amount))

        def settled_remove_liquidity() -> dict[str | None, tuple[Decimal, Decimal]] | None:
            current_position_liquidity = self.actual_position_liquidity_amount(pool)
            current_claims = self.claim_balances_by_token(pool)
            if (
                current_position_liquidity < before_position_liquidity
                and self.claimable_increased(
                    before_claims,
                    current_claims,
                    require_all=True,
                )
            ):
                self.validate_position_interfaces(pool)
                return current_claims
            return None

        claims = self.wait_for("remove liquidity claimable output and kline projection", settled_remove_liquidity)
        self.claim_balances_and_wait(pool, claims, "remove liquidity")
        return self.actual_position_liquidity_amount(pool)

    def execute_remove_liquidity(self, pool: Pool, remove_amount: str) -> None:
        self.application_graphql(
            self.user_wallet_url,
            self.user_chain_id,
            pool.application_id,
            """
            mutation RemoveLiquidity($liquidity: Amount!, $amount0OutMin: Amount, $amount1OutMin: Amount, $to: Account) {
              removeLiquidity(liquidity: $liquidity, amount0OutMin: $amount0OutMin, amount1OutMin: $amount1OutMin, to: $to)
            }
            """,
            {
                "liquidity": remove_amount,
                "amount0OutMin": "0",
                "amount1OutMin": "0",
                "to": self.account(self.user_chain_id, self.user_owner),
            },
        )

    def execute_oversupplied_add_liquidity_claim_path(self, pool: Pool) -> None:
        before_claims = self.claim_balances_by_token(pool)
        before_liquidity = self.owner_liquidity_amount(pool)

        self.execute_add_liquidity(pool, amount_0_in="1", amount_1_in="1")

        def settled_oversupply() -> dict[str | None, tuple[Decimal, Decimal]] | None:
            current_claims = self.claim_balances_by_token(pool)
            current_liquidity = self.owner_liquidity_amount(pool)
            if current_liquidity > before_liquidity and self.claimable_increased(
                before_claims,
                current_claims,
                require_all=False,
            ):
                return current_claims
            return None

        claims = self.wait_for("oversupplied add liquidity claimable excess", settled_oversupply)
        self.claim_balances_and_wait(pool, claims, "oversupplied add liquidity")
        print("[product-e2e] oversupplied add liquidity claim completed")

    def execute_failed_add_liquidity_claim_path(self, pool: Pool) -> None:
        before_claims = self.claim_balances_by_token(pool)
        before_liquidity = self.owner_liquidity_amount(pool)

        self.execute_add_liquidity(
            pool,
            amount_0_in="0.1",
            amount_1_in="0.1",
            amount_0_out_min="1000000000",
            amount_1_out_min="1000000000",
        )

        def settled_failure() -> dict[str | None, tuple[Decimal, Decimal]] | None:
            current_claims = self.claim_balances_by_token(pool)
            current_liquidity = self.owner_liquidity_amount(pool)
            if current_liquidity == before_liquidity and self.claimable_increased(
                before_claims,
                current_claims,
                require_all=True,
            ):
                return current_claims
            return None

        claims = self.wait_for("failed add liquidity claimable refund", settled_failure)
        self.claim_balances_and_wait(pool, claims, "failed add liquidity")
        print("[product-e2e] failed add liquidity claim completed")

    def claim_balances_by_token(self, pool: Pool) -> dict[str | None, tuple[Decimal, Decimal]]:
        return {token: self.claim_balances(pool, token) for token in self.pool_claim_tokens(pool)}

    def claim_balances(self, pool: Pool, token: str | None) -> tuple[Decimal, Decimal]:
        balances = self.application_graphql(
            self.query_url,
            pool.pool_application_chain,
            pool.application_id,
            """
            query ClaimBalances($token: ApplicationId, $owner: Account!) {
              claimableBalance(token: $token, owner: $owner)
              claimingBalance(token: $token, owner: $owner)
            }
            """,
            {"token": token, "owner": self.account(self.user_chain_id, self.user_owner)},
        )
        return Decimal(str(balances["claimableBalance"])), Decimal(str(balances["claimingBalance"]))

    def claimable_increased(
        self,
        before: dict[str | None, tuple[Decimal, Decimal]],
        current: dict[str | None, tuple[Decimal, Decimal]],
        *,
        require_all: bool,
    ) -> bool:
        deltas = [
            current[token][0] - before[token][0]
            for token in self.pool_claim_tokens_from_balances(before)
        ]
        if require_all:
            return all(delta > 0 for delta in deltas)
        return any(delta > 0 for delta in deltas)

    def claim_balances_and_wait(
        self,
        pool: Pool,
        balances: dict[str | None, tuple[Decimal, Decimal]],
        label: str,
    ) -> None:
        claimed = False
        for token, (claimable, _) in balances.items():
            if claimable <= 0:
                continue
            print(
                f"[product-e2e] claiming {label} token={self.token_label(token)} amount={claimable}"
            )
            self.application_graphql(
                self.user_wallet_url,
                self.user_chain_id,
                pool.application_id,
                """
                mutation Claim($token: ApplicationId, $amount: Amount!) {
                  claim(token: $token, amount: $amount)
                }
                """,
                {"token": token, "amount": str(claimable)},
            )
            claimed = True

        if not claimed:
            raise E2EError(f"{label} produced no claimable balance")

        def settled_claims() -> bool | None:
            current = self.claim_balances_by_token(pool)
            for claimable, claiming in current.values():
                if claimable > 0 or claiming > 0:
                    return None
            return True

        self.wait_for(f"{label} claim settlement", settled_claims)

    def check_claim_capability(self, pool: Pool) -> None:
        balances = self.claim_balances_by_token(pool)
        for token, (claimable, claiming) in balances.items():
            print(
                f"[product-e2e] claim balances token={self.token_label(token)}: "
                f"claimable={claimable} claiming={claiming}"
            )
        if self.strict_claim and any(
            claimable > 0 or claiming > 0 for claimable, claiming in balances.values()
        ):
            raise E2EError("strict claim requested, but claim balances did not settle")

    def check_observability(self, pool: Pool) -> None:
        stats = self.http_json(f"{self.kline_url}/protocol/stats")
        current_pools = self.swap_pools()
        observed_pool_count = int(stats.get("pool_count", 0))
        if observed_pool_count < len(current_pools):
            raise E2EError(
                f"kline protocol pool_count does not cover swap pools: {observed_pool_count} < {len(current_pools)}"
            )
        expected_tvl_floor = self.expected_tvl_native(current_pools)
        observed_tvl = self.decimal_or_zero(stats.get("tvl"))
        if expected_tvl_floor <= 0:
            raise E2EError("independently computed protocol TVL is not positive")
        if observed_tvl <= 0:
            raise E2EError(f"protocol stats TVL is not positive: {observed_tvl}")
        minimum_tvl = expected_tvl_floor * Decimal("0.99")
        if observed_tvl < minimum_tvl:
            raise E2EError(
                f"protocol stats TVL is too far below current swap pools: {observed_tvl} < {minimum_tvl}"
            )
        rows = self.transaction_rows(limit=500)
        if not rows:
            raise E2EError("kline transactions endpoint returned no rows")
        pool_rows = [row for row in rows if self.observability_row_matches_pool(row, pool)]
        if not pool_rows:
            raise E2EError(f"kline transactions endpoint has no recent rows for pool {pool.pool_id}")
        self.assert_observability_trade_transactions(pool_rows, pool)
        self.validate_position_interfaces(pool)

    def assert_observability_trade_transactions(self, rows: list[dict], pool: Pool) -> None:
        observed_types = {str(row.get("transaction_type") or "") for row in rows}
        if not observed_types & self.swap_transaction_types():
            raise E2EError(f"kline transactions for pool {pool.pool_id} did not include a swap: {observed_types}")
        for row in rows:
            if self.decimal_or_zero(row.get("timestamp")) <= 0 and self.decimal_or_zero(row.get("created_at")) <= 0:
                raise E2EError(f"kline transaction has no positive timestamp: {row}")
            tx_type = row.get("transaction_type")
            if tx_type not in self.swap_transaction_types():
                raise E2EError(f"kline transactions endpoint returned non-trade row: {row}")
            if (
                self.decimal_or_zero(row.get("amount_0_in"))
                + self.decimal_or_zero(row.get("amount_0_out"))
                + self.decimal_or_zero(row.get("amount_1_in"))
                + self.decimal_or_zero(row.get("amount_1_out"))
                <= 0
            ):
                raise E2EError(f"kline swap transaction has no positive token movement: {row}")

    def wait_for_pool(self, token_0: str, token_1: str | None) -> Pool:
        def find_pool() -> Pool | None:
            for pool in self.swap_pools():
                if pool.token_0 == token_0 and pool.token_1 == token_1:
                    self.pool_chain_id = pool.pool_application_chain
                    if pool.reserve_0 > 0 and pool.reserve_1 > 0:
                        return pool
            return None

        return self.wait_for("initialized pool", find_pool)

    def wait_for_transaction(self, pool: Pool, types: set[str]) -> None:
        def has_transaction() -> bool | None:
            seen = self.transaction_types(pool, limit=200)
            return bool(seen & types) or None

        self.wait_for(f"transaction {sorted(types)}", has_transaction)

    def transaction_types(self, pool: Pool, *, limit: int) -> set[str]:
        transactions = self.transaction_rows(limit=limit)
        return {
            row.get("transaction_type")
            for row in transactions
            if isinstance(row, dict) and self.observability_row_matches_pool(row, pool)
        }

    def transaction_rows(self, *, limit: int) -> list[dict]:
        now_ms = int(time.time() * 1000)
        start_at = 0
        end_at = now_ms + 300000
        transactions = self.http_json(
            f"{self.kline_url}/transactions/start_at/{start_at}/end_at/{end_at}?limit={limit}"
        )
        payload = transactions.get("data", transactions) if isinstance(transactions, dict) else transactions
        rows = payload if isinstance(payload, list) else payload.get("transactions", [])
        return [row for row in rows if isinstance(row, dict)]

    def transaction_count(self, pool: Pool, types: set[str]) -> int:
        return sum(
            1
            for row in self.transaction_rows(limit=300)
            if isinstance(row, dict)
            and self.observability_row_matches_pool(row, pool)
            and row.get("transaction_type") in types
        )

    def latest_transaction_id(self, pool: Pool, types: set[str]) -> int:
        latest = 0
        for row in self.transaction_rows(limit=300):
            if (
                isinstance(row, dict)
                and self.observability_row_matches_pool(row, pool)
                and row.get("transaction_type") in types
            ):
                latest = max(latest, int(self.decimal_or_zero(row.get("transaction_id"))))
        return latest

    def wait_for_actual_position_fee(self, pool: Pool) -> None:
        def has_fee() -> bool | None:
            self.validate_position_interfaces(pool, require_actual_fee_positive=True)
            return True

        self.wait_for("actual position trading-fee projection", has_fee)

    def wait_for_virtual_protocol_fee(self, pool: Pool) -> None:
        def has_fee() -> bool | None:
            self.validate_position_interfaces(pool, require_virtual_protocol_fee_positive=True)
            return True

        self.wait_for("virtual protocol-fee projection", has_fee)


    def validate_initial_virtual_position_interfaces(self, pool: Pool) -> None:
        positions = self.position_rows_for_pool(pool)
        metrics = self.position_metrics_for_pool(pool)
        if not positions:
            raise E2EError(f"initial /positions has no rows for pool {pool.pool_id}")
        if not metrics:
            raise E2EError(f"initial /position-metrics has no rows for pool {pool.pool_id}")

        actual_positions = [row for row in positions if self.is_actual_position(row)]
        if actual_positions:
            raise E2EError(f"initial virtual-liquidity pool should not expose actual LP rows: {actual_positions}")

        virtual_positions = [row for row in positions if self.is_virtual_position(row)]
        if len(virtual_positions) != 1:
            raise E2EError(f"expected exactly one initial virtual position for pool {pool.pool_id}, got {virtual_positions}")
        virtual_position = virtual_positions[0]
        virtual_amount0 = self.decimal_or_zero(virtual_position.get("virtual_initial_amount0"))
        virtual_amount1 = self.decimal_or_zero(virtual_position.get("virtual_initial_amount1"))
        if virtual_amount0 <= 0 or virtual_amount1 < 0:
            raise E2EError(f"initial virtual position has invalid bootstrap amounts: {virtual_position}")

        virtual_metric = self.single_metric(metrics, status="virtual")
        self.assert_metric_amounts_balance(virtual_metric, protocol_fee_expected=True)
        protocol_fee_total = self.metric_protocol_fee_total(virtual_metric)
        if protocol_fee_total < 0:
            raise E2EError(f"initial virtual protocol fee metric cannot be negative: {virtual_metric}")
        if self.decimal_or_zero(virtual_metric.get("redeemable_amount0")) == virtual_amount0:
            raise E2EError(f"initial virtual metric leaked bootstrap token0 as redeemable amount: {virtual_metric}")
        if virtual_amount1 > 0 and self.decimal_or_zero(virtual_metric.get("redeemable_amount1")) == virtual_amount1:
            raise E2EError(f"initial virtual metric leaked bootstrap token1 as redeemable amount: {virtual_metric}")

    def validate_position_interfaces(
        self,
        pool: Pool,
        *,
        require_actual_fee_positive: bool = False,
        require_virtual_protocol_fee_positive: bool = False,
    ) -> None:
        positions = self.position_rows_for_pool(pool)
        metrics = self.position_metrics_for_pool(pool)
        if not positions:
            raise E2EError(f"/positions has no rows for pool {pool.pool_id}")
        if not metrics:
            raise E2EError(f"/position-metrics has no rows for pool {pool.pool_id}")

        actual_positions = [row for row in positions if self.is_actual_position(row)]
        if len(actual_positions) > 1:
            raise E2EError(f"/positions returned multiple actual rows for pool {pool.pool_id}: {actual_positions}")
        if actual_positions:
            actual = actual_positions[0]
            actual_liquidity = self.decimal_or_zero(actual.get("current_liquidity"))
            metric_status = "closed" if actual_liquidity <= 0 else "active"
            metric = self.single_metric(metrics, status=metric_status)
            self.assert_decimal_equal(
                actual.get("current_liquidity"),
                metric.get("current_liquidity"),
                "actual /positions.current_liquidity vs /position-metrics.current_liquidity",
            )
            self.assert_decimal_equal(
                actual.get("current_liquidity"),
                metric.get("position_liquidity"),
                "actual /positions.current_liquidity vs /position-metrics.position_liquidity",
            )
            self.assert_metric_amounts_balance(metric, protocol_fee_expected=False)
            if require_actual_fee_positive:
                if not self.metric_snapshot_available(metric):
                    raise E2EError(f"actual position metrics snapshot is unavailable for pool {pool.pool_id}: {metric}")
                if self.metric_fee_total(metric) <= 0:
                    raise E2EError(f"actual position trading fees are not positive for pool {pool.pool_id}: {metric}")
                if self.metric_trailing_fee_total(metric) <= 0:
                    raise E2EError(f"actual position trailing 24h fees are not positive for pool {pool.pool_id}: {metric}")

        virtual_positions = [row for row in positions if self.is_virtual_position(row)]
        virtual_metric = None
        if virtual_positions:
            virtual_metric = self.single_metric(metrics, status="virtual")
            self.assert_metric_amounts_balance(virtual_metric, protocol_fee_expected=True)
            self.assert_virtual_protocol_fee_liquidity_matches_pool_snapshot(pool, virtual_metric)
            if require_virtual_protocol_fee_positive and self.metric_protocol_fee_total(virtual_metric) <= 0:
                raise E2EError(f"virtual protocol fees are not positive for pool {pool.pool_id}: {virtual_metric}")

        contract_liquidity = self.owner_liquidity_amount(pool)
        projected_liquidity = sum(self.decimal_or_zero(row.get("current_liquidity")) for row in positions)
        residual_liquidity = contract_liquidity - projected_liquidity
        if residual_liquidity < Decimal("-0.000000000000000001"):
            raise E2EError(
                f"contract owner liquidity {contract_liquidity} is below projected /positions liquidity "
                f"{projected_liquidity} for pool {pool.pool_id}"
            )
        if virtual_metric is not None:
            self.assert_decimal_equal(
                residual_liquidity,
                virtual_metric.get("current_liquidity"),
                "contract owner liquidity residual vs virtual protocol-fee current_liquidity",
            )

    def assert_metric_amounts_balance(self, metric: dict, *, protocol_fee_expected: bool) -> None:
        amount_0 = self.decimal_or_zero(metric.get("redeemable_amount0"))
        components_0 = (
            self.decimal_or_zero(metric.get("principal_amount0"))
            + self.decimal_or_zero(metric.get("fee_amount0"))
            + self.decimal_or_zero(metric.get("protocol_fee_amount0"))
        )
        self.assert_decimal_equal(amount_0, components_0, "metric token0 redeemable amount components")

        amount_1 = self.decimal_or_zero(metric.get("redeemable_amount1"))
        components_1 = (
            self.decimal_or_zero(metric.get("principal_amount1"))
            + self.decimal_or_zero(metric.get("fee_amount1"))
            + self.decimal_or_zero(metric.get("protocol_fee_amount1"))
        )
        self.assert_decimal_equal(amount_1, components_1, "metric token1 redeemable amount components")

        protocol_total = self.metric_protocol_fee_total(metric)
        if protocol_fee_expected and protocol_total < 0:
            raise E2EError(f"protocol fee metric cannot be negative: {metric}")
        if not protocol_fee_expected and protocol_total != 0:
            raise E2EError(f"actual LP metric should not include protocol fee amounts: {metric}")

    def assert_virtual_protocol_fee_liquidity_matches_pool_snapshot(self, pool: Pool, metric: dict) -> None:
        pool_state_snapshot = self.debug_pool_state_snapshot(pool)
        total_minted = self.decimal_or_zero(pool_state_snapshot.get("total_minted_protocol_fee"))
        pending = self.decimal_or_zero(pool_state_snapshot.get("pending_protocol_fee"))
        expected_liquidity = total_minted + pending
        if expected_liquidity <= 0:
            return
        self.assert_decimal_equal(
            metric.get("position_liquidity"),
            expected_liquidity,
            "virtual protocol-fee position_liquidity vs pool minted+pending protocol fee",
        )
        self.assert_decimal_equal(
            metric.get("total_supply"),
            self.decimal_or_zero(pool_state_snapshot.get("current_total_supply")) + pending,
            "virtual protocol-fee total_supply vs pool total supply plus pending protocol fee",
        )

    def debug_pool_state_snapshot(self, pool: Pool) -> dict:
        params = urllib.parse.urlencode({
            "pool_application": self.pool_application_account(pool),
            "pool_id": pool.pool_id,
            "owner": self.owner_account_string(),
            "transaction_limit": 1,
            "diagnostics_limit": 1,
        })
        payload = self.http_json(f"{self.kline_url}/debug/pool?{params}")
        snapshot = payload.get("pool_state_snapshot") if isinstance(payload, dict) else None
        if not isinstance(snapshot, dict):
            raise E2EError(f"debug pool state snapshot is unavailable for pool {pool.pool_id}: {payload}")
        return snapshot

    def actual_position_liquidity_amount(self, pool: Pool) -> Decimal:
        row = self.actual_position_row(pool)
        if row is None:
            return Decimal("0")
        return self.decimal_or_zero(row.get("current_liquidity"))

    def actual_position_row(self, pool: Pool) -> dict | None:
        rows = [row for row in self.position_rows_for_pool(pool) if self.is_actual_position(row)]
        if len(rows) > 1:
            raise E2EError(f"multiple actual position rows for pool {pool.pool_id}: {rows}")
        return rows[0] if rows else None

    def position_rows_for_pool(self, pool: Pool) -> list[dict]:
        return [
            row
            for row in self.kline_positions(status="all")
            if row.get("pool_application") == self.pool_application_account(pool)
        ]

    def position_metrics_for_pool(self, pool: Pool) -> list[dict]:
        return [
            row
            for row in self.kline_position_metrics(status="all")
            if row.get("pool_application") == self.pool_application_account(pool)
        ]

    def kline_positions(self, *, status: str) -> list[dict]:
        params = urllib.parse.urlencode({"owner": self.owner_account_string(), "status": status})
        payload = self.http_json(f"{self.kline_url}/positions?{params}")
        rows = payload.get("positions", []) if isinstance(payload, dict) else []
        return [row for row in rows if isinstance(row, dict)]

    def kline_position_metrics(self, *, status: str) -> list[dict]:
        params = urllib.parse.urlencode({"owner": self.owner_account_string(), "status": status})
        payload = self.http_json(f"{self.kline_url}/position-metrics?{params}")
        rows = payload.get("metrics", []) if isinstance(payload, dict) else []
        return [row for row in rows if isinstance(row, dict)]

    def single_metric(self, metrics: list[dict], *, status: str) -> dict:
        rows = [row for row in metrics if row.get("status") == status]
        if len(rows) != 1:
            raise E2EError(f"expected exactly one {status} /position-metrics row, got {len(rows)}: {rows}")
        return rows[0]

    @staticmethod
    def is_actual_position(row: dict) -> bool:
        return (
            row.get("status") != "virtual"
            and not bool(row.get("is_virtual_position"))
            and row.get("position_kind") != "virtual_initial_liquidity"
        )

    @staticmethod
    def is_virtual_position(row: dict) -> bool:
        return (
            row.get("status") == "virtual"
            or bool(row.get("is_virtual_position"))
            or row.get("position_kind") == "virtual_initial_liquidity"
        )

    @staticmethod
    def metric_snapshot_available(metric: dict) -> bool:
        return "missing_position_metrics_snapshot" not in (metric.get("computation_blockers") or [])

    @staticmethod
    def metric_fee_total(metric: dict) -> Decimal:
        return ProductWorkflowE2E.decimal_or_zero(metric.get("fee_amount0")) + ProductWorkflowE2E.decimal_or_zero(metric.get("fee_amount1"))

    @staticmethod
    def metric_trailing_fee_total(metric: dict) -> Decimal:
        return ProductWorkflowE2E.decimal_or_zero(metric.get("trailing_24h_fee_amount0")) + ProductWorkflowE2E.decimal_or_zero(metric.get("trailing_24h_fee_amount1"))

    @staticmethod
    def metric_protocol_fee_total(metric: dict) -> Decimal:
        return ProductWorkflowE2E.decimal_or_zero(metric.get("protocol_fee_amount0")) + ProductWorkflowE2E.decimal_or_zero(metric.get("protocol_fee_amount1"))

    @staticmethod
    def assert_decimal_equal(left, right, label: str) -> None:
        left_decimal = ProductWorkflowE2E.decimal_or_zero(left)
        right_decimal = ProductWorkflowE2E.decimal_or_zero(right)
        if abs(left_decimal - right_decimal) > Decimal("0.000000000000000001"):
            raise E2EError(f"{label} mismatch: {left_decimal} != {right_decimal}")

    @staticmethod
    def swap_transaction_types() -> set[str]:
        return {"BuyToken0", "SellToken0", "Swap"}

    def expected_tvl_native(self, pools: list[Pool]) -> Decimal:
        native_prices: dict[str, Decimal] = {"TLINERA": Decimal("1")}
        edges = []
        for pool in pools:
            token_0 = pool.token_0
            token_1 = self.normalized_token(pool.token_1)
            if pool.reserve_0 <= 0 or pool.reserve_1 <= 0:
                continue
            edges.append((token_0, token_1, pool.reserve_1 / pool.reserve_0))
            edges.append((token_1, token_0, pool.reserve_0 / pool.reserve_1))

        changed = True
        while changed:
            changed = False
            for from_token, to_token, price_in_to_token in edges:
                if from_token in native_prices or to_token not in native_prices:
                    continue
                native_prices[from_token] = price_in_to_token * native_prices[to_token]
                changed = True

        tvl = Decimal("0")
        for pool in pools:
            token_0 = pool.token_0
            token_1 = self.normalized_token(pool.token_1)
            if token_0 in native_prices:
                tvl += pool.reserve_0 * native_prices[token_0]
            if token_1 in native_prices:
                tvl += pool.reserve_1 * native_prices[token_1]
        return tvl

    @staticmethod
    def normalized_token(token: str | None) -> str:
        return "TLINERA" if token is None else str(token)

    def owner_liquidity_amount(self, pool: Pool) -> Decimal:
        liquidity = self.pool_liquidity(pool)
        return Decimal(str(liquidity.get("liquidity", "0")))

    def meme_balance(self, token: str, owner: dict) -> Decimal:
        data = self.application_graphql(
            self.query_url,
            self.meme_chain_for_token(token),
            token,
            """
            query BalanceOf($owner: Account!) {
              balanceOf(owner: $owner)
            }
            """,
            {"owner": owner},
        )
        return Decimal(str(data["balanceOf"]))

    def native_owner_balance(self, chain_id: str, owner: str) -> Decimal:
        data = self.graphql(
            self.user_wallet_url,
            """
            query Balances($chainOwners: [ChainOwners!]!) {
              balances(chainOwners: $chainOwners)
            }
            """,
            {"chainOwners": [{"chainId": chain_id, "owners": [owner]}]},
        )
        chain_balances = data["balances"].get(chain_id, {})
        owner_balances = chain_balances.get("ownerBalances", {})
        return Decimal(str(owner_balances.get(owner, "0")))

    def meme_chain_for_token(self, token: str) -> str:
        chain_id = self.meme_chains.get(token)
        if chain_id:
            return chain_id
        applications = self.proxy_meme_applications()
        chain_id = applications.get(token)
        if not chain_id:
            raise E2EError(f"cannot resolve meme chain for token {token}")
        self.meme_chains[token] = chain_id
        return chain_id

    def owner_account_string(self) -> str:
        return f"{self.user_owner}@{self.user_chain_id}"

    def pool_application_account(self, pool: Pool) -> str:
        return f"{pool.pool_application_owner}@{pool.pool_application_chain}"

    def observability_row_matches_pool(self, row: dict, pool: Pool) -> bool:
        pool_application = row.get("pool_application")
        if pool_application:
            return pool_application == self.pool_application_account(pool)
        return int(row.get("pool_id") or 0) == int(pool.pool_id)

    def pool_liquidity(self, pool: Pool) -> dict:
        return self.application_graphql(
            self.query_url,
            pool.pool_application_chain,
            pool.application_id,
            """
            query Liquidity($owner: Account!) {
              liquidity(owner: $owner) { liquidity amount0 amount1 }
            }
            """,
            {"owner": self.account(self.user_chain_id, self.user_owner)},
        )["liquidity"]

    def pool_state(self, pool: Pool) -> Pool:
        current = self.find_pool(pool.pool_id)
        if current is None:
            raise E2EError(f"pool not found: {pool.pool_id}")
        return current

    def find_pool(self, pool_id: int) -> Pool | None:
        for pool in self.swap_pools():
            if pool.pool_id == pool_id:
                return pool
        return None

    def swap_pools(self) -> list[Pool]:
        data = self.application_graphql(
            self.query_url,
            self.swap_chain_id,
            self.swap_application_id,
            """
            query Pools {
              pools { poolId token0 token1 poolApplication reserve0 reserve1 token0Price token1Price }
            }
            """,
            {},
        )
        pools = []
        for item in data["pools"]:
            pool_application = self.parse_account(item["poolApplication"])
            pools.append(
                Pool(
                    pool_id=int(item["poolId"]),
                    token_0=item["token0"],
                    token_1=item["token1"],
                    pool_application_chain=pool_application["chain_id"],
                    pool_application_owner=pool_application["owner"],
                    reserve_0=self.decimal_or_zero(item["reserve0"]),
                    reserve_1=self.decimal_or_zero(item["reserve1"]),
                )
            )
        return pools

    def publish_logo_blob(self) -> str:
        logo_bytes = list(f"product-e2e-logo-{self.run_id}".encode("utf-8"))
        data = self.graphql(
            self.user_wallet_url,
            "mutation PublishDataBlob($chainId: ChainId!, $bytes: [Int!]!) { publishDataBlob(chainId: $chainId, bytes: $bytes) }",
            {"chainId": self.user_chain_id, "bytes": logo_bytes},
        )
        return data["publishDataBlob"]

    def proxy_meme_tokens(self) -> set[str]:
        return set(self.proxy_meme_applications())

    def proxy_meme_applications(self) -> dict[str, str]:
        data = self.application_graphql(
            self.query_url,
            self.proxy_chain_id,
            self.proxy_application_id,
            "query MemeApplications { memeApplications { chainId token } }",
            {},
        )
        return {item["token"]: item["chainId"] for item in data["memeApplications"]}

    def default_chain_id(self) -> str:
        if self.user_chain_override:
            return self.user_chain_override
        data = self.graphql(self.user_wallet_url, "query Chains { chains { default } }", {})
        return data["chains"]["default"]

    def chain_owner(self, chain_id: str) -> str:
        if self.user_owner_override:
            return self.user_owner_override
        if not self.wallet_path.exists():
            raise E2EError(f"user wallet file not found: {self.wallet_path}")
        wallet = json.loads(self.wallet_path.read_text())
        chain = wallet.get("chains", {}).get(chain_id)
        owner = chain.get("owner") if isinstance(chain, dict) else None
        if not owner:
            raise E2EError(f"cannot resolve owner for chain {chain_id} from {self.wallet_path}")
        return owner

    def process_known_inboxes(self) -> None:
        routes = [
            (self.user_wallet_url, self.user_chain_id),
            (self.proxy_wallet_url, self.proxy_chain_id),
            (self.swap_wallet_url, self.swap_chain_id),
            (self.swap_wallet_url, self.pool_chain_id),
        ]
        routes.extend((self.proxy_wallet_url, chain_id) for chain_id in self.meme_chains.values())
        for wallet_url, chain_id in dict.fromkeys(routes):
            route = (wallet_url, chain_id)
            if not chain_id or route in self.skipped_inbox_routes:
                continue
            try:
                self.drain_inbox(wallet_url, chain_id)
            except E2EError as error:
                if self.is_non_proposable_chain_error(error):
                    self.skipped_inbox_routes.add(route)
                    print(f"[product-e2e] skipping inbox pump for non-proposable chain: {wallet_url} {chain_id}")
                    continue
                raise

    @staticmethod
    def is_non_proposable_chain_error(error: Exception) -> bool:
        message = str(error)
        return (
            "client is not configured to propose on chain" in message
            or "ChainClient was not configured to propose new blocks" in message
        )
    def drain_inbox(self, wallet_url: str, chain_id: str) -> None:
        for _ in range(self.max_inbox_drain_rounds):
            processed = self.process_inbox(wallet_url, chain_id)
            if not processed:
                return

    def process_inbox(self, wallet_url: str, chain_id: str) -> list[str]:
        data = self.graphql(
            wallet_url,
            "mutation ProcessInbox($chainId: ChainId!) { processInbox(chainId: $chainId) }",
            {"chainId": chain_id},
        )
        return data.get("processInbox") or []

    def application_graphql(self, base_url: str, chain_id: str, application_id: str, query: str, variables: dict) -> dict:
        return self.graphql(f"{base_url}/chains/{chain_id}/applications/{application_id}", query, variables)

    def graphql(self, url: str, query: str, variables: dict) -> dict:
        payload = {"query": query, "variables": variables}
        response = self.http_json(url, payload)
        if response.get("errors"):
            raise E2EError(f"GraphQL errors from {url}: {json.dumps(response['errors'], ensure_ascii=False)}")
        data = response.get("data")
        if data is None:
            raise E2EError(f"GraphQL response from {url} has no data: {response}")
        return data

    def http_json(self, url: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        def timeout_handler(_signum, _frame):
            raise TimeoutError(f"HTTP request exceeded {self.request_timeout_seconds}s for {url}")

        previous_handler = signal.signal(signal.SIGALRM, timeout_handler)
        if self.request_timeout_seconds and self.request_timeout_seconds > 0:
            signal.alarm(int(self.request_timeout_seconds))
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as error:
            raise E2EError(str(error)) from error
        except urllib.error.HTTPError as error:
            raise E2EError(f"HTTP {error.code} from {url}: {error.read().decode('utf-8', 'replace')}") from error
        except urllib.error.URLError as error:
            raise E2EError(f"HTTP request failed for {url}: {error}") from error
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)

    def wait_for(self, label: str, probe):
        deadline = None if self.timeout_seconds is None else time.time() + self.timeout_seconds
        last_error = None
        while deadline is None or time.time() < deadline:
            try:
                self.process_known_inboxes()
                value = probe()
                if value:
                    return value
            except Exception as error:
                last_error = error
            time.sleep(self.poll_seconds)
        if last_error is not None:
            raise E2EError(f"timed out waiting for {label}; last error: {last_error}") from last_error
        raise E2EError(f"timed out waiting for {label}")

    @staticmethod
    def account(chain_id: str, owner: str) -> dict:
        return {"chain_id": chain_id, "owner": owner}

    @staticmethod
    def parse_account(value) -> dict:
        if isinstance(value, dict):
            return {
                "chain_id": value.get("chain_id") or value.get("chainId"),
                "owner": value.get("owner") or "0x00",
            }
        if isinstance(value, str) and "@" in value:
            owner, chain_id = value.split("@", 1)
            return {"chain_id": chain_id, "owner": owner}
        raise E2EError(f"cannot parse account value: {value}")

    @staticmethod
    def decimal_or_zero(value) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def pool_claim_tokens(pool: Pool) -> list[str | None]:
        return [pool.token_0, pool.token_1]

    @staticmethod
    def pool_claim_tokens_from_balances(
        balances: dict[str | None, tuple[Decimal, Decimal]]
    ) -> list[str | None]:
        return list(balances)

    @staticmethod
    def token_label(token: str | None) -> str:
        return "native" if token is None else token


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local full product workflow E2E.")
    parser.add_argument("--user-wallet-url", default="http://localhost:40092")
    parser.add_argument("--proxy-wallet-url", default="http://localhost:23080")
    parser.add_argument("--swap-wallet-url", default="http://localhost:22080")
    parser.add_argument("--query-url", default="http://localhost:24080")
    parser.add_argument("--kline-url", default="http://localhost:25080")
    parser.add_argument("--proxy-chain-id", required=True)
    parser.add_argument("--proxy-application-id", required=True)
    parser.add_argument("--swap-chain-id", required=True)
    parser.add_argument("--swap-application-id", required=True)
    parser.add_argument("--ams-application-id", required=True)
    parser.add_argument("--blob-gateway-application-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=0, help="Maximum seconds to wait for each condition; <=0 waits forever")
    parser.add_argument("--request-timeout-seconds", type=int, default=180)
    parser.add_argument("--poll-seconds", type=int, default=5)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--user-wallet-file", default="output/local/wallet/user/0/wallet.json")
    parser.add_argument("--user-chain-id", default="")
    parser.add_argument("--user-owner", default="")
    parser.add_argument("--strict-claim", action="store_true")
    return parser


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    args = build_arg_parser().parse_args()
    ProductWorkflowE2E(args).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
