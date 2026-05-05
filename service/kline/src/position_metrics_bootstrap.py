import async_request
from decimal import Decimal

from account_codec import AccountCodec
from position_metrics_fee_free_open_state_simulator import PositionMetricsFeeFreeOpenStateSimulator
from position_metrics_liquidity_history_analyzer import PositionMetricsLiquidityHistoryAnalyzer
from position_metrics_pool_history_reconstructor import PositionMetricsPoolHistoryReconstructor
from position_metrics_pool_history_replay_inspector import PositionMetricsPoolHistoryReplayInspector
from position_metrics_swap_math_support import PositionMetricsSwapMathSupport
from position_metrics_value_support import PositionMetricsValueSupport
from query.read_models.position_metrics_fetch_coordinator import PositionMetricsFetchCoordinator
from query.read_models.position_metrics_fast_path_executor import PositionMetricsFastPathExecutor
from query.read_models.position_metrics_fast_path_plan_builder import PositionMetricsFastPathPlanBuilder
from query.read_models.position_metrics_payload_only_executor import PositionMetricsPayloadOnlyExecutor
from query.read_models.position_metrics_replay_fallback_executor import PositionMetricsReplayFallbackExecutor
from query.read_models.position_metrics_replay_fallback_result_builder import PositionMetricsReplayFallbackResultBuilder
from query.read_models.position_metrics_replay_snapshot_shadow_builder import PositionMetricsReplaySnapshotShadowBuilder
from query.read_models.position_metrics_projection_payload_adapter import PositionMetricsProjectionPayloadAdapter
from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator
from position_metrics_entrypoint import PositionMetricsEntrypoint
from position_metrics_estimated_fallback_resolver import PositionMetricsEstimatedFallbackResolver
from position_metrics_fee_to_opening_mint_resolver import PositionMetricsFeeToOpeningMintResolver
from position_metrics_history_enricher import PositionMetricsHistoryEnricher
from position_metrics_history_semantic_resolver import PositionMetricsHistorySemanticResolver
from position_metrics_live_payload_api import PositionMetricsLivePayloadApi
from position_metrics_live_payload_fetcher import PositionMetricsLivePayloadFetcher
from position_metrics_no_swap_exact_resolver import PositionMetricsNoSwapExactResolver
from position_metrics_partial_result_builder import PositionMetricsPartialResultBuilder
from position_metrics_payload_decision_resolver import PositionMetricsPayloadDecisionResolver
from position_metrics_payload_enricher import PositionMetricsPayloadEnricher
from position_metrics_payload_planner import PositionMetricsPayloadPlanner
from position_metrics_payload_semantic_builder import PositionMetricsPayloadSemanticBuilder
from position_metrics_public_api import PositionMetricsPublicApi
from position_metrics_replay_entrypoint import PositionMetricsReplayEntrypoint
from position_metrics_swap_history_alignment_checker import PositionMetricsSwapHistoryAlignmentChecker
from position_metrics_swap_history_exact_materializer import PositionMetricsSwapHistoryExactMaterializer
from position_metrics_swap_history_exactness_solver import PositionMetricsSwapHistoryExactnessSolver
from position_metrics_swap_history_exactness_validator import PositionMetricsSwapHistoryExactnessValidator
from position_metrics_swap_history_precheck import PositionMetricsSwapHistoryPrecheck
from position_metrics_warning_applier import PositionMetricsWarningApplier


class PositionMetricsBootstrap:
    EPSILON = Decimal('0.000000000001')
    DISPLAY_QUANTUM = Decimal('0.000000000000000001')
    ATTOS_SCALE = 10 ** 18
    LIQUIDITY_MINT_TOLERANCE_ATTOS = 100
    SWAP_OUT_TOLERANCE_ATTOS = 1
    SWAP_FEE_NUMERATOR = 997
    SWAP_FEE_DENOMINATOR = 1000

    def __init__(self):
        self.account_codec = AccountCodec()
        self.default_post = async_request.post
        self._pool_application_support = None
        self._live_payload_api = None
        self._entrypoint = None
        self._replay_entrypoint = None
        self._projection_payload_adapter = None
        self._snapshot_shadow_evaluator = None
        self._swap_history_exactness_solver = None
        self._history_enricher = None
        self._payload_enricher = None
        self._payload_planner = None
        self._public_api = None
        self._partial_result_builder = None
        self._warning_applier = None
        self._value_support = None
        self._liquidity_history_analyzer = None
        self._default_swap_math_support = None
        self._pool_history_reconstructor = None
        self._pool_history_replay_inspector = None
        self._fee_free_open_state_simulator = None

    def public_api(self):
        if self._public_api is None:
            self._public_api = PositionMetricsPublicApi(
                live_payload_api=self.live_payload_api(),
                entrypoint=self.entrypoint(),
                replay_entrypoint=self.replay_entrypoint(),
                fetcher_factory=self,
                default_post=self.default_post,
                default_swap_out_tolerance_attos=self.SWAP_OUT_TOLERANCE_ATTOS,
            )
        return self._public_api

    def live_payload_api(self) -> PositionMetricsLivePayloadApi:
        if self._live_payload_api is None:
            from integration.pool_application_client import PoolApplicationClient
            self._live_payload_api = PositionMetricsLivePayloadApi(
                account_codec=self.account_codec,
                pool_application_client_type=PoolApplicationClient,
                payload_fetcher=PositionMetricsLivePayloadFetcher(
                    parse_account=self.parse_account,
                ),
            )
        return self._live_payload_api

    def build(
        self,
        *,
        query_input_provider,
    ):
        fetch_coordinator = PositionMetricsFetchCoordinator(
            payload_builder=lambda *, position, snapshot_inputs: self.projection_payload_adapter().build_payload(
                position=position,
                snapshot_inputs=snapshot_inputs,
            ),
            query_input_provider=query_input_provider,
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(
                snapshot_fast_path=PositionMetricsSnapshotFastPath(
                    snapshot_shadow_evaluator=self.snapshot_shadow_evaluator(),
                ),
            ),
            plan_payload=self.entrypoint().plan_position_metrics_from_payload,
            fast_path_executor=PositionMetricsFastPathExecutor(),
            payload_only_executor=PositionMetricsPayloadOnlyExecutor(),
            replay_fallback_executor=PositionMetricsReplayFallbackExecutor(
                enrich_payload=self.entrypoint().enrich_position_metrics_from_payload_result,
                replay_snapshot_shadow_builder=PositionMetricsReplaySnapshotShadowBuilder(
                    snapshot_shadow_evaluator=self.snapshot_shadow_evaluator(),
                ),
                replay_fallback_result_builder=PositionMetricsReplayFallbackResultBuilder(),
            ),
        )

        async def fetch(position: dict):
            return await fetch_coordinator.fetch(position=position)

        return fetch

    def replay_entrypoint(self):
        if self._replay_entrypoint is None:
            self._replay_entrypoint = PositionMetricsReplayEntrypoint(
                pool_history_replay_inspector=self.pool_history_replay_inspector(),
                pool_history_reconstructor=self.pool_history_reconstructor(),
                fee_free_open_state_simulator=self.fee_free_open_state_simulator(),
                mint_fee_attos=self.mint_fee_attos,
            )
        return self._replay_entrypoint

    def swap_history_exactness_solver(self):
        if self._swap_history_exactness_solver is None:
            self._swap_history_exactness_solver = PositionMetricsSwapHistoryExactnessSolver(
                validator=PositionMetricsSwapHistoryExactnessValidator(
                    precheck=PositionMetricsSwapHistoryPrecheck(
                        to_decimal=self.to_decimal,
                        history_liquidity=self.history_liquidity,
                    ),
                    alignment_checker=PositionMetricsSwapHistoryAlignmentChecker(
                        replay_entrypoint=self.replay_entrypoint(),
                        fee_to_opening_mint_resolver=PositionMetricsFeeToOpeningMintResolver(
                            history_liquidity_before=self.history_liquidity_before,
                            split_protocol_fee_redeemable_attos=self.split_protocol_fee_redeemable_attos,
                            from_attos=self.from_attos,
                            epsilon=self.EPSILON,
                        ),
                        attos_within_tolerance=self.attos_within_tolerance,
                        to_attos=self.to_attos,
                    ),
                ),
                materializer=PositionMetricsSwapHistoryExactMaterializer(
                    from_attos=self.from_attos,
                    normalize_non_negative=self.normalize_non_negative,
                    serialize_decimal=self.serialize_decimal,
                ),
            )
        return self._swap_history_exactness_solver

    def history_enricher(self):
        if self._history_enricher is None:
            self._history_enricher = PositionMetricsHistoryEnricher(
                to_decimal=self.to_decimal,
                history_liquidity=self.history_liquidity,
                try_enrich_metrics_with_swap_history=self.swap_history_exactness_solver().solve,
                semantic_resolver=PositionMetricsHistorySemanticResolver(
                    no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                        serialize_decimal=self.serialize_decimal,
                    ),
                    estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                        build_estimated_metrics_from_liquidity_history=self.build_estimated_metrics_from_liquidity_history,
                    ),
                ),
            )
        return self._history_enricher

    def payload_enricher(self):
        if self._payload_enricher is None:
            self._payload_enricher = PositionMetricsPayloadEnricher(
                payload_semantic_builder=PositionMetricsPayloadSemanticBuilder(
                    build_partial_metrics=self.build_partial_metrics,
                    account_payload_to_string=self.account_payload_to_string,
                ),
                payload_decision_resolver=PositionMetricsPayloadDecisionResolver(),
                enrich_metrics_with_history=self.history_enricher().enrich,
                apply_data_quality_warnings=self.apply_data_quality_warnings,
                build_transaction_gap_summary=self.build_transaction_gap_summary,
            )
        return self._payload_enricher

    def payload_planner(self):
        if self._payload_planner is None:
            self._payload_planner = PositionMetricsPayloadPlanner(
                payload_semantic_builder=PositionMetricsPayloadSemanticBuilder(
                    build_partial_metrics=self.build_partial_metrics,
                    account_payload_to_string=self.account_payload_to_string,
                ),
                payload_decision_resolver=PositionMetricsPayloadDecisionResolver(),
                apply_data_quality_warnings=self.apply_data_quality_warnings,
                build_transaction_gap_summary=self.build_transaction_gap_summary,
            )
        return self._payload_planner

    def entrypoint(self):
        if self._entrypoint is None:
            self._entrypoint = PositionMetricsEntrypoint(
                payload_planner=self.payload_planner(),
                payload_enricher=self.payload_enricher(),
            )
        return self._entrypoint

    def projection_payload_adapter(self):
        if self._projection_payload_adapter is None:
            self._projection_payload_adapter = PositionMetricsProjectionPayloadAdapter()
        return self._projection_payload_adapter

    def snapshot_shadow_evaluator(self):
        if self._snapshot_shadow_evaluator is None:
            self._snapshot_shadow_evaluator = PositionMetricsSnapshotShadowEvaluator()
        return self._snapshot_shadow_evaluator

    def parse_account(self, account: str):
        return self.account_codec.payload_account_from_public_account(account)

    def account_payload_to_string(self, account: object) -> str | None:
        return self.account_codec.public_account_from_payload(account)

    def build_partial_metrics(self, liquidity, total_supply_value, virtual_initial_liquidity: bool):
        if self._partial_result_builder is None:
            self._partial_result_builder = PositionMetricsPartialResultBuilder()
        return self._partial_result_builder.build(
            liquidity,
            total_supply_value,
            virtual_initial_liquidity,
        )

    def apply_data_quality_warnings(
        self,
        metrics: dict,
        *,
        pool_history_gap_summary: dict | None = None,
    ) -> dict:
        if self._warning_applier is None:
            self._warning_applier = PositionMetricsWarningApplier()
        return self._warning_applier.apply(
            metrics,
            pool_history_gap_summary=pool_history_gap_summary,
        )

    def value_support(self) -> PositionMetricsValueSupport:
        if self._value_support is None:
            self._value_support = PositionMetricsValueSupport(
                attos_scale=self.ATTOS_SCALE,
                display_quantum=self.DISPLAY_QUANTUM,
                epsilon=self.EPSILON,
                liquidity_mint_tolerance_attos=self.LIQUIDITY_MINT_TOLERANCE_ATTOS,
                swap_out_tolerance_attos=self.SWAP_OUT_TOLERANCE_ATTOS,
            )
        return self._value_support

    def liquidity_history_analyzer(self) -> PositionMetricsLiquidityHistoryAnalyzer:
        if self._liquidity_history_analyzer is None:
            self._liquidity_history_analyzer = PositionMetricsLiquidityHistoryAnalyzer(
                to_decimal=self.to_decimal,
                to_attos=self.to_attos,
                from_attos=self.from_attos,
                normalize_non_negative=self.normalize_non_negative,
                serialize_decimal=self.serialize_decimal,
                split_protocol_fee_redeemable_attos=self.split_protocol_fee_redeemable_attos,
                fee_numerator=self.SWAP_FEE_NUMERATOR,
                fee_denominator=self.SWAP_FEE_DENOMINATOR,
            )
        return self._liquidity_history_analyzer

    def default_swap_math_support(self) -> PositionMetricsSwapMathSupport:
        if self._default_swap_math_support is None:
            self._default_swap_math_support = self._build_swap_math_support(
                swap_fee_numerator=self.SWAP_FEE_NUMERATOR,
                swap_fee_denominator=self.SWAP_FEE_DENOMINATOR,
            )
        return self._default_swap_math_support

    def pool_history_reconstructor(self) -> PositionMetricsPoolHistoryReconstructor:
        if self._pool_history_reconstructor is None:
            self._pool_history_reconstructor = PositionMetricsPoolHistoryReconstructor(
                to_attos=self.to_attos,
                swap_expected_out_attos=self.swap_expected_out_attos,
                swap_out_within_tolerance=self.swap_out_within_tolerance,
                infer_hidden_swap_before_batch=self.infer_hidden_swap_before_batch,
                apply_recorded_swap_attos=self.apply_recorded_swap_attos,
                sqrt_attos_product=self.sqrt_attos_product,
                mint_fee_attos=self.mint_fee_attos,
                attos_within_tolerance=self.attos_within_tolerance,
            )
        return self._pool_history_reconstructor

    def pool_history_replay_inspector(self) -> PositionMetricsPoolHistoryReplayInspector:
        if self._pool_history_replay_inspector is None:
            self._pool_history_replay_inspector = PositionMetricsPoolHistoryReplayInspector(
                to_attos=self.to_attos,
                swap_expected_out_attos=self.swap_expected_out_attos,
                swap_out_within_tolerance=self.swap_out_within_tolerance,
                infer_hidden_swap_before_batch=self.infer_hidden_swap_before_batch,
                apply_recorded_swap_attos=self.apply_recorded_swap_attos,
                sqrt_attos_product=self.sqrt_attos_product,
                mint_fee_attos=self.mint_fee_attos,
                attos_within_tolerance=self.attos_within_tolerance,
                serialize_attos_debug=self._serialize_attos_debug,
            )
        return self._pool_history_replay_inspector

    def fee_free_open_state_simulator(self) -> PositionMetricsFeeFreeOpenStateSimulator:
        if self._fee_free_open_state_simulator is None:
            self._fee_free_open_state_simulator = PositionMetricsFeeFreeOpenStateSimulator(
                to_attos=self.to_attos,
            )
        return self._fee_free_open_state_simulator

    def to_decimal(self, value):
        return self.value_support().to_decimal(value)

    def serialize_decimal(self, value: Decimal | None):
        return self.value_support().serialize_decimal(value)

    def build_transaction_gap_summary(
        self,
        transaction_history: list[dict] | None,
        *,
        start_id: int | None = None,
        end_id: int | None = None,
        sample_limit: int = 8,
    ) -> dict:
        transaction_ids = sorted(
            {
                int(tx.get('transaction_id'))
                for tx in (transaction_history or [])
                if tx.get('transaction_id') is not None
            }
        )
        if not transaction_ids:
            return self._gap_summary(
                start_id=None,
                end_id=None,
                missing_count=0,
                missing_ids_sample=[],
            )
        lower_bound = transaction_ids[0] if start_id is None else max(int(start_id), transaction_ids[0])
        upper_bound = transaction_ids[-1] if end_id is None else min(int(end_id), transaction_ids[-1])
        if lower_bound > upper_bound:
            return self._gap_summary(
                start_id=lower_bound,
                end_id=upper_bound,
                missing_count=0,
                missing_ids_sample=[],
            )
        return self._gap_summary(
            start_id=lower_bound,
            end_id=upper_bound,
            missing_count=0,
            missing_ids_sample=[],
            sample_limit=sample_limit,
        )

    def to_attos(self, value) -> int | None:
        return self.value_support().to_attos(value)

    def from_attos(self, value: int | None) -> Decimal | None:
        return self.value_support().from_attos(value)

    def attos_within_tolerance(
        self,
        left: int,
        right: int,
        tolerance: int | None = None,
    ) -> bool:
        return self.value_support().attos_within_tolerance(
            left,
            right,
            self.LIQUIDITY_MINT_TOLERANCE_ATTOS if tolerance is None else tolerance,
        )

    def swap_out_within_tolerance(
        self,
        left: int,
        right: int,
        tolerance: int | None = None,
    ) -> bool:
        return self.value_support().swap_out_within_tolerance(
            left,
            right,
            self.SWAP_OUT_TOLERANCE_ATTOS if tolerance is None else tolerance,
        )

    def split_protocol_fee_redeemable_attos(
        self,
        *,
        redeemable_amount0: Decimal,
        redeemable_amount1: Decimal,
        live_liquidity: Decimal,
        history_liquidity: Decimal,
    ) -> tuple[int, int]:
        return self.value_support().split_protocol_fee_redeemable_attos(
            redeemable_amount0=redeemable_amount0,
            redeemable_amount1=redeemable_amount1,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )

    def history_liquidity(self, liquidity_history: list[dict]) -> Decimal:
        return self.liquidity_history_analyzer().history_liquidity(liquidity_history)

    def history_net_token_amounts(self, liquidity_history: list[dict]) -> tuple[Decimal, Decimal]:
        return self.value_support().history_net_token_amounts(liquidity_history)

    def latest_position_liquidity_tx(self, liquidity_history: list[dict]) -> dict | None:
        return self.liquidity_history_analyzer().latest_position_liquidity_tx(liquidity_history)

    def build_observed_swap_fee_estimate(
        self,
        *,
        pool_transaction_history: list[dict] | None,
        latest_position_tx: dict | None,
        liquidity_basis: Decimal,
        total_supply_live: Decimal,
    ) -> tuple[Decimal, Decimal]:
        return self.liquidity_history_analyzer().build_observed_swap_fee_estimate(
            pool_transaction_history=pool_transaction_history,
            latest_position_tx=latest_position_tx,
            liquidity_basis=liquidity_basis,
            total_supply_live=total_supply_live,
        )

    def build_estimated_metrics_from_liquidity_history(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        live_liquidity: Decimal | None,
        history_liquidity: Decimal,
    ) -> dict:
        return self.liquidity_history_analyzer().build_estimated_metrics_from_liquidity_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )

    def history_liquidity_before(
        self,
        liquidity_history: list[dict],
        latest_position_tx: dict,
    ) -> Decimal:
        return self.liquidity_history_analyzer().history_liquidity_before(liquidity_history, latest_position_tx)

    def normalize_non_negative(
        self,
        value: Decimal,
        tolerance: Decimal | None = None,
    ) -> Decimal:
        return self.value_support().normalize_non_negative(
            value,
            self.EPSILON if tolerance is None else tolerance,
        )

    def mint_fee_attos(self, total_supply: int, reserve0: int, reserve1: int, k_last: int) -> int:
        return self.default_swap_math_support().mint_fee_attos(total_supply, reserve0, reserve1, k_last)

    def sqrt_attos_product(self, amount0: int | None, amount1: int | None) -> int | None:
        return self.default_swap_math_support().sqrt_attos_product(amount0, amount1)

    def swap_expected_out_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        amount0_in: int,
        amount1_in: int,
        *,
        fee_numerator: int | None = None,
        fee_denominator: int | None = None,
    ) -> int | None:
        return self._build_swap_math_support(
            swap_fee_numerator=self.SWAP_FEE_NUMERATOR if fee_numerator is None else fee_numerator,
            swap_fee_denominator=self.SWAP_FEE_DENOMINATOR if fee_denominator is None else fee_denominator,
        ).swap_expected_out_attos(
            tx_type,
            reserve0,
            reserve1,
            amount0_in,
            amount1_in,
        )

    def apply_recorded_swap_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        *,
        amount0_in: int,
        amount0_out: int,
        amount1_in: int,
        amount1_out: int,
    ) -> tuple[int, int]:
        return self.default_swap_math_support().apply_recorded_swap_attos(
            tx_type,
            reserve0,
            reserve1,
            amount0_in=amount0_in,
            amount0_out=amount0_out,
            amount1_in=amount1_in,
            amount1_out=amount1_out,
        )

    def infer_hidden_swap_before_batch(
        self,
        reserve0: int,
        reserve1: int,
        pool_transaction_history: list[dict],
        index: int,
    ) -> dict | None:
        return self.default_swap_math_support().infer_hidden_swap_before_batch(
            reserve0,
            reserve1,
            pool_transaction_history,
            index,
        )

    def is_close(
        self,
        left: Decimal | None,
        right: Decimal | None,
        tolerance: Decimal | None = None,
    ) -> bool:
        return self.value_support().is_close(
            left,
            right,
            self.EPSILON if tolerance is None else tolerance,
        )

    def _gap_summary(
        self,
        *,
        start_id,
        end_id,
        missing_count: int,
        missing_ids_sample: list[int],
        sample_limit: int = 8,
    ) -> dict:
        return {
            'has_internal_gaps': False,
            'start_id': start_id,
            'end_id': end_id,
            'missing_count': missing_count,
            'missing_ids_sample': missing_ids_sample[:sample_limit],
            'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
        }

    def _build_swap_math_support(
        self,
        *,
        swap_fee_numerator: int,
        swap_fee_denominator: int,
    ) -> PositionMetricsSwapMathSupport:
        return PositionMetricsSwapMathSupport(
            to_attos=self.to_attos,
            from_attos=self.from_attos,
            swap_fee_numerator=swap_fee_numerator,
            swap_fee_denominator=swap_fee_denominator,
            swap_out_tolerance_attos=self.SWAP_OUT_TOLERANCE_ATTOS,
        )

    def _serialize_attos_debug(self, value: int | None) -> str | None:
        if value is None:
            return None
        return str(value)
