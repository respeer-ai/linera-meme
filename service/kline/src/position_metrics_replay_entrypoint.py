class PositionMetricsReplayEntrypoint:
    def __init__(
        self,
        *,
        pool_history_replay_inspector,
        pool_history_reconstructor,
        fee_free_open_state_simulator,
        mint_fee_attos,
    ):
        self.pool_history_replay_inspector = pool_history_replay_inspector
        self.pool_history_reconstructor = pool_history_reconstructor
        self.fee_free_open_state_simulator = fee_free_open_state_simulator
        self.mint_fee_attos = mint_fee_attos

    def inspect_pool_history_replay(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
        swap_out_tolerance_attos: int,
    ) -> dict:
        return self.pool_history_replay_inspector.inspect(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )

    def reconstruct_pool_history(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
    ) -> tuple[list[dict] | None, list[dict] | None, list[str]]:
        return self.pool_history_reconstructor.reconstruct(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
        )

    def effective_total_supply_attos_from_state(self, state: dict) -> int:
        return state['total_supply_after'] + self.mint_fee_attos(
            state['total_supply_after'],
            state['reserve0_after'],
            state['reserve1_after'],
            state['k_last_after'],
        )

    def simulate_fee_free_from_open_state(
        self,
        states: list[dict],
        pool_transaction_history: list[dict],
        start_index: int,
    ) -> tuple[dict, list[str]]:
        return self.fee_free_open_state_simulator.simulate(
            states,
            pool_transaction_history,
            start_index,
        )
