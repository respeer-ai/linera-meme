from account_codec import AccountCodec
from market.settled_market_result import SettledMarketResult


class SettledOutputBatch:
    def __init__(
        self,
        *,
        outputs: list[dict[str, object]],
        account_codec=None,
    ):
        self.outputs = list(outputs)
        self.account_codec = account_codec or AccountCodec()

    def trades(self) -> list[dict[str, object]]:
        return [
            output
            for output in self.outputs
            if output.get('settled_output_type') == SettledMarketResult.OUTPUT_SETTLED_TRADE
        ]

    def liquidity_changes(self) -> list[dict[str, object]]:
        return [
            output
            for output in self.outputs
            if output.get('settled_output_type') == SettledMarketResult.OUTPUT_SETTLED_LIQUIDITY_CHANGE
        ]

    def affected_pools(self) -> list[tuple[str, str | None]]:
        pools = {
            (
                str(output['pool_application_id']),
                self._string_or_none(output.get('pool_chain_id')),
            )
            for output in self.outputs
            if output.get('pool_application_id') is not None
        }
        return sorted(pools)

    def affected_positions(self) -> list[tuple[str, str, str | None]]:
        positions = {
            (
                self._public_owner(str(output['owner'])),
                str(output['pool_application_id']),
                self._string_or_none(output.get('pool_chain_id')),
            )
            for output in self.liquidity_changes()
            if output.get('owner') is not None
            and output.get('pool_application_id') is not None
        }
        return sorted(positions)

    def _public_owner(self, owner: str) -> str:
        parsed = self.account_codec.parse_account(owner)
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)
