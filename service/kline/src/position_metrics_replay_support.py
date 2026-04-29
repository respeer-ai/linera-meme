class PositionMetricsReplaySupport:
    def __init__(
        self,
        *,
        pool_history_reconstructor_factory,
        pool_history_replay_inspector_factory,
        fee_free_open_state_simulator_factory,
        mint_fee_attos,
    ):
        self.pool_history_reconstructor_factory = pool_history_reconstructor_factory
        self.pool_history_replay_inspector_factory = pool_history_replay_inspector_factory
        self.fee_free_open_state_simulator_factory = fee_free_open_state_simulator_factory
        self.mint_fee_attos = mint_fee_attos

    def reconstruct_pool_history(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
    ) -> tuple[list[dict] | None, list[dict] | None, list[str]]:
        return self.pool_history_reconstructor_factory().reconstruct(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
        )

    def inspect_pool_history_replay(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
        swap_out_tolerance_attos: int,
    ) -> dict:
        return self.pool_history_replay_inspector_factory().inspect(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )

    def simulate_pool_history(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
    ) -> tuple[list[dict] | None, list[str]]:
        _, states, blockers = self.reconstruct_pool_history(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
        )
        if blockers:
            return None, blockers
        return states, []

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
        return self.fee_free_open_state_simulator_factory().simulate(
            states,
            pool_transaction_history,
            start_index,
        )
