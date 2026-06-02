#!/usr/bin/env python3
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
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
        self.timeout_seconds = args.timeout_seconds
        self.request_timeout_seconds = args.request_timeout_seconds
        self.poll_seconds = args.poll_seconds
        self.strict_claim = args.strict_claim
        self.run_id = args.run_id or str(int(time.time()))
        self.wallet_path = Path(args.user_wallet_file)
        self.user_chain_override = args.user_chain_id
        self.user_owner_override = args.user_owner

        self.user_chain_id = ""
        self.user_owner = ""
        self.meme_chain_id = ""
        self.pool_chain_id = ""

    def run(self) -> None:
        self.user_chain_id = self.default_chain_id()
        self.user_owner = self.chain_owner(self.user_chain_id)
        print(f"[product-e2e] user chain: {self.user_chain_id}")
        print(f"[product-e2e] user owner: {self.user_owner}")

        before_tokens = self.proxy_meme_tokens()
        token = self.create_meme_and_wait(before_tokens)
        self.created_token = token
        print(f"[product-e2e] meme token: {token}")

        pool = self.wait_for_pool(token_0=token, token_1=NATIVE_TOKEN)
        print(f"[product-e2e] pool: {pool.pool_id} {pool.application_id}@{pool.pool_application_chain}")

        pool = self.execute_swap_and_wait(pool)
        print("[product-e2e] swap completed")

        liquidity = self.execute_add_liquidity_and_wait(pool)
        print(f"[product-e2e] add liquidity completed: {liquidity}")

        self.execute_remove_liquidity_and_wait(pool, liquidity)
        print("[product-e2e] remove liquidity completed")

        self.execute_oversupplied_add_liquidity_claim_path(pool)
        self.execute_failed_add_liquidity_claim_path(pool)

        self.check_claim_capability(pool)
        self.check_observability(pool)
        print("[product-e2e] completed")

    def create_meme_and_wait(self, before_tokens: set[str]) -> str:
        logo_hash = self.publish_logo_blob()
        ticker = f"E2E{self.run_id[-8:]}".upper()
        variables = {
            "memeInstantiationArgument": {
                "meme": {
                    "initialSupply": "21000000",
                    "totalSupply": "21000000",
                    "name": f"Product E2E {self.run_id}",
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
                self.meme_chain_id = applications[token]
                return token
            return None

        return self.wait_for("meme token creation", created_token)

    def execute_swap_and_wait(self, pool: Pool) -> Pool:
        before = self.pool_state(pool)
        self.execute_swap(pool)

        def changed_pool() -> Pool | None:
            current = self.find_pool(pool.pool_id)
            if current and (current.reserve_0 != before.reserve_0 or current.reserve_1 != before.reserve_1):
                return current
            return None

        return self.wait_for("pool reserve change after swap", changed_pool)

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
        before = self.owner_liquidity_amount(pool)
        self.execute_add_liquidity(pool)

        def increased_liquidity() -> Decimal | None:
            current = self.owner_liquidity_amount(pool)
            if current > before:
                return current
            return None

        return self.wait_for("user liquidity increase after add liquidity", increased_liquidity)

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
            raise E2EError("remove liquidity cannot run because user liquidity is zero")
        remove_amount = Decimal("0.1") if liquidity >= Decimal("0.1") else liquidity
        owner = self.account(self.user_chain_id, self.user_owner)
        before_token_0 = self.meme_balance(pool.token_0, owner)
        before_token_1 = self.meme_balance(pool.token_1, owner) if pool.token_1 else None
        before_native = self.native_owner_balance(self.user_chain_id, self.user_owner) if pool.token_1 is None else None

        self.execute_remove_liquidity(pool, str(remove_amount))

        def settled_remote_liquidity() -> Decimal | None:
            current_liquidity = self.owner_liquidity_amount(pool)
            current_token_0 = self.meme_balance(pool.token_0, owner)
            token_0_received = current_token_0 > before_token_0

            token_1_received = True
            if pool.token_1:
                token_1_received = self.meme_balance(pool.token_1, owner) > before_token_1

            native_received = True
            if before_native is not None:
                native_received = self.native_owner_balance(self.user_chain_id, self.user_owner) > before_native

            if current_liquidity < liquidity and token_0_received and token_1_received and native_received:
                return current_liquidity
            return None

        return self.wait_for("remote liquidity payout after remove liquidity", settled_remote_liquidity)

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
        if int(stats.get("pool_count", 0)) <= 0:
            raise E2EError("kline protocol stats did not observe any pools")
        rows = self.transaction_rows(limit=50)
        if not rows:
            raise E2EError("kline transactions endpoint returned no rows")

    def wait_for_pool(self, token_0: str, token_1: str | None) -> Pool:
        def find_pool() -> Pool | None:
            for pool in self.swap_pools():
                if pool.token_0 == token_0 and pool.token_1 == token_1:
                    self.pool_chain_id = pool.pool_application_chain
                    if pool.reserve_0 > 0 and pool.reserve_1 > 0:
                        return pool
            return None

        return self.wait_for("initialized pool", find_pool)

    def wait_for_transaction(self, pool_id: int, types: set[str]) -> None:
        def has_transaction() -> bool | None:
            seen = self.transaction_types(pool_id, limit=200)
            return bool(seen & types) or None

        self.wait_for(f"transaction {sorted(types)}", has_transaction)

    def transaction_types(self, pool_id: int, *, limit: int) -> set[str]:
        transactions = self.transaction_rows(limit=limit)
        return {
            row.get("transaction_type")
            for row in transactions
            if isinstance(row, dict) and int(row.get("pool_id") or 0) == int(pool_id)
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
        if token == getattr(self, "created_token", "") and self.meme_chain_id:
            return self.meme_chain_id
        applications = self.proxy_meme_applications()
        chain_id = applications.get(token)
        if not chain_id:
            raise E2EError(f"cannot resolve meme chain for token {token}")
        return chain_id

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
            (self.proxy_wallet_url, self.meme_chain_id),
            (self.swap_wallet_url, self.pool_chain_id),
        ]
        for wallet_url, chain_id in dict.fromkeys(routes):
            if chain_id:
                self.process_inbox(wallet_url, chain_id)

    def process_inbox(self, wallet_url: str, chain_id: str) -> None:
        self.graphql(
            wallet_url,
            "mutation ProcessInbox($chainId: ChainId!) { processInbox(chainId: $chainId) }",
            {"chainId": chain_id},
        )

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
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise E2EError(f"HTTP {error.code} from {url}: {error.read().decode('utf-8', 'replace')}") from error
        except urllib.error.URLError as error:
            raise E2EError(f"HTTP request failed for {url}: {error}") from error

    def wait_for(self, label: str, probe):
        deadline = time.time() + self.timeout_seconds
        last_error = None
        while time.time() < deadline:
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
    parser.add_argument("--timeout-seconds", type=int, default=900)
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
