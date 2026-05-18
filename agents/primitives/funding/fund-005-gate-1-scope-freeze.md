# FUND-005 Gate 1 Scope Freeze

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Define the canonical review organization for `FUND-005` Gate 1. Review and approval proceed sub-gate by sub-gate. Do not batch the full Gate 1 scope freeze into one delivery.

## Rules

- Review Gate 1 through these sub-gates only:
  1. `Gate 1A`: audit layers
  2. `Gate 1B`: in-scope files
  3. `Gate 1C`: fixed protocol paths
  4. `Gate 1D`: exclusions
  5. `Gate 1E`: audit dimensions and Gate 2 format constraints
- Do not start a later sub-gate before the earlier sub-gate is reviewed and accepted.
- Do not repeat the full Gate 1 body in later prompts. Reference this file and include only the current sub-gate content under review.
- Do not use vague scope terms such as `related`, `as needed`, `etc`, or similar expandable wording.
- Do not treat a prose summary as approval. Each sub-gate must be reviewable item by item.

## Gate 1A Audit Layers

`FUND-005` Gate 2 must organize the current implementation audit table through these fixed layers and in this order:

1. Protocol definition layer
2. Runtime abstraction layer
3. Contract dispatch boundary layer
4. Contract handler layer
5. Persistent state layer
6. Product entry and truth boundary layer
7. Test baseline layer

### Gate 1A Layer Definitions

1. Protocol definition layer
   - Authority:
     - `abi/`
   - Purpose:
     - define operation, message, response, and payload shapes
     - define instantiation argument shapes
     - define service query and query-response shapes used by product funding paths
     - define token, account, and chain identity shapes used by funding workflows
   - Must answer:
     - which funding protocol objects currently exist
     - which instantiation arguments currently exist
     - which are public operations
     - which are internal messages
     - which are response or callback carriers
     - which service query and query-response objects are funding-relevant
     - whether claim, fail, and bounce closure objects already exist
     - whether `CreatePool`, `InitializeLiquidity`, `AddLiquidity`, `Swap`, `RemoveLiquidity`, `CreateMeme`, `Mine`, and `Redeem` already have explicit funding, balance-accrual, or funds-exit semantics

2. Runtime abstraction layer
   - Authority:
     - `runtime/`
   - Purpose:
     - define capabilities exposed to contracts, not business workflow ownership
     - define authenticated caller, message context, application-call context, access control, message send capability, application-call capability, direct transfer capability, application creation capability, chain opening capability, application-permission capability, bounce capability, and close-chain capability
   - Must answer:
     - how contracts currently obtain caller, source, app, and message context
     - whether `call_application` capability is exposed
     - whether message send capability is exposed
     - whether direct native transfer capability is exposed
     - whether direct combined owner/application transfer capability is exposed
     - whether application creation capability is exposed
     - whether chain opening capability is exposed
     - whether application-permission read/write capability is exposed
     - whether bounce detection capability is exposed
     - whether close-chain capability is exposed
     - which runtime capabilities required by later funding iterations already exist and which are missing
     - whether runtime send capability currently applies authentication by default
     - whether runtime send capability currently applies tracking by default
     - whether close-chain is a current capability or a target capability gap
     - where each exposed capability is consumed by handler architecture, without treating capability exposure as workflow ownership

3. Contract dispatch boundary layer
   - Authority:
     - each funding contract's `contract.rs`
     - each funding contract's `contract_impl.rs`
   - Purpose:
     - define instantiation entry dispatch
     - define operation entry dispatch
     - define message entry dispatch
     - define outgoing message send boundary
     - define bounced-message receive boundary
   - Must answer:
     - where instantiation is dispatched
     - where operations are dispatched
     - where messages are dispatched
     - whether instantiation creates funding-relevant state, applications, chains, permissions, transactions, or outgoing messages
     - where `.send_message(...)` actually sends
     - whether authentication and tracking are attached here or scattered in business handlers
     - whether bounced messages have an explicit dispatch entry
     - what the real send modifiers are, without assuming design intent equals current implementation

4. Contract handler layer
   - Authority:
     - handler boundary:
       - each funding contract's `contract_inner/handlers/*`
     - instantiation-handler boundary:
       - each funding contract's `contract_inner/instantiation_handler*`
     - contract-impl instantiation boundary:
       - instantiation-side business behavior inside each funding contract's `contract_impl.rs`
   - Purpose:
     - define current business behavior, state transition logic, checks, and side effects
   - Must answer:
     - what each current handler actually does
     - what instantiation-side business behavior does when it creates funding-relevant state or messages
     - which handlers act as callback consumers
     - which handlers act as receipt consumers
     - which source, authenticated-caller, application, intent, token, amount, owner, and state checks each callback or receipt consumer performs
     - which runtime capabilities each handler consumes
     - where `call_application(...)` is actually initiated
     - where direct native transfer or combined transfer is actually initiated
     - where mining reward minting and meme redeem balance exit are actually initiated
     - whether direct transfer occurs inside liquidity, swap, remove, refund, payout, initialization, or claim-like behavior
     - which state preconditions each handler relies on
     - which economic states each handler mutates
     - how each handler treats invalid input, duplicate input, and stale follow-up
     - whether owner, intent, token, or amount is currently inferred from signer or payload where it should not be
     - whether late guards are currently substituting for real terminal truth
     - whether funds exit currently happens inside a workflow that should later credit claim balances instead

5. Persistent state layer
   - Authority:
     - each funding contract's `interfaces/state*`
     - each funding contract's `state*`
   - Purpose:
     - define protocol truth storage for active, pending, finalized, failed, reserve, LP, payout, refund, claim, and claiming state
   - Must answer:
     - which state fields are initialized by instantiation before any operation or message
     - which fields currently determine whether a pool is active
     - which fields currently determine whether reserves are finalized
     - which fields currently determine whether LP is minted or burned
     - which fields currently determine mining reward state, mined token balances, and redeemable meme-chain balances
     - whether claim and claiming balance truth already exists
     - whether terminal truth is unique
     - whether double truth exists
     - whether late guards currently stand in for real terminal truth

6. Product entry and truth boundary layer
   - Authority:
     - frontend entry boundary:
       - frontend funding operation submission chain
       - frontend GraphQL read layer
     - contract service boundary:
       - contract `service.rs` query surface
       - contract `service.rs` mutation surface when used by product entry
     - observability fact/projection boundary:
       - `service/kline/` raw fact ingestion
       - `service/kline/` application discovery and registry persistence
       - `service/kline/` decoder and registry selection
       - `service/kline/` normalized event family mapping
       - `service/kline/` projection and market/funding derivation
       - `service/kline/` projection-backed query and serializer boundary
       - `service/kline/` debug and diagnostic visibility for pending, stalled, and failed workflows
     - product truth boundary:
       - `service/kline/` projection-backed funding truth
   - Purpose:
     - define how users enter funding workflows
     - define how products read funding prerequisites
     - define where product truth is projection-backed versus live-query-backed
   - Must answer:
     - which frontend entries submit funding operations
     - what the frontend operation submission chain is beyond page components
     - which GraphQL or read paths are used to determine pair existence, meme application existence, creator chain, and create-pool versus add-liquidity routing
     - where account, application, and token identity are normalized before chain submission
     - what the wallet-type-specific submission capability matrix is across funding operations
     - which funding-relevant query and mutation surfaces contract `service.rs` exposes
     - which raw facts are needed for funding workflow visibility
     - which application discovery and registry persistence entries are needed for funding workflow visibility
     - which decoder and registry entries are needed for funding workflow visibility
     - which normalized event families are needed for funding workflow visibility
     - which projections derive claim balances, claiming balances, pending workflows, stalled workflows, failed workflows, pool lifecycle, reserves, LP, positions, TVL, APR inputs, and diagnostics
     - which query handlers, read models, serializers, and repositories expose projected funding truth
     - which product truths come from projections
     - which product truths still depend on live query
     - whether stalled, pending, and failed workflows are visible to product or diagnostics
   - Scope requirements:
     - page entry layer
     - route and flow decision layer
     - store layer
     - wallet and provider adapter layer
     - protocol utility layer
     - frontend GraphQL read layer
     - account, application, and token identity normalization boundary
     - wallet-type-specific submission capability boundary
     - contract `service.rs` query surface
     - contract `service.rs` mutation surface when the frontend or product entry actually depends on it
     - raw fact ingestion boundary
     - application discovery and registry persistence boundary
     - decoder and registry boundary
     - normalized event family boundary
     - projection and market/funding derivation boundary
     - projection-backed query and serializer boundary
     - debug and diagnostic visibility boundary
   - Required product-entry semantics:
     - `CreatePool`
     - `InitializeLiquidity`
     - `AddLiquidity`
     - `Swap`
     - `RemoveLiquidity`
     - `CreateMeme`

7. Test baseline layer
   - Authority:
     - runtime capability test boundary
     - base handler and dispatch support test boundary
     - funding contract test boundary
     - contract service test boundary
     - observability fact/projection test boundary
     - frontend funding-entry test boundary
   - Purpose:
     - define what current behavior is already locked by tests
     - define which current behaviors still need characterization before refactor
   - Must answer:
     - which runtime capabilities are already locked by tests
     - which base handler outcome and dispatch message-shape behaviors are already locked by tests
     - which send authentication and tracking behaviors are already locked by tests
     - which missing bounce and close-chain capability gaps have characterization coverage
     - which funding behaviors are already locked by contract tests
     - which meme mining and redeem balance-exit behaviors are already locked by contract tests
     - which funding-related contract service query or mutation semantics are locked by service tests
     - which raw ingestion, decoder, registry, normalizer, projection, query/read-model, serializer, and diagnostic visibility behaviors are already locked by tests
     - which pending, stalled, and failed workflow visibility behaviors are already locked by tests
     - which funding entry semantics are locked by frontend baseline tests
     - which funding routing and mode-selection semantics are locked by baseline tests
     - which funding submission semantics are locked by baseline tests
     - which critical behaviors still lack characterization tests
     - which behaviors must be locked before protocol mutation

### Gate 1A Acceptance Criteria

Gate 1A is accepted only if:

1. The seven layers are complete.
2. The layer order is accepted.
3. Layers 1, 2, 3, and 5 each have one clear authority boundary.
4. Each layer has one clear purpose boundary.
5. Layer 1 explicitly includes operation, message, response, instantiation argument, service query, and service query-response shapes.
6. Layer 2 explicitly includes `call_application` and runtime send-capability reality checks.
7. Layer 2 explicitly treats runtime as a capability boundary and not as business workflow ownership.
8. Layer 2 explicitly includes direct transfer capability, application creation capability, chain opening capability, application-permission capability, and close-chain current-vs-target capability checks.
9. Layer 3 explicitly includes instantiation dispatch and `send_message` dispatch-boundary reality checks.
10. Layer 3 explicitly includes instantiation-side funding state, transaction, application, chain, permission, and outgoing-message side effects.
11. Layer 4 has exactly these three authority sub-boundaries:
   - handler boundary
   - instantiation-handler boundary
   - contract-impl instantiation boundary
12. Layer 4 explicitly includes actual handler-side `call_application`, direct transfer, payout, refund, and funds-exit location checks.
13. Layer 4 explicitly includes instantiation-side business behavior inside `contract_inner/instantiation_handler*` and `contract_impl.rs`.
14. Layer 4 explicitly includes callback and receipt consumer checks.
15. Layer 5 explicitly includes state initialized by instantiation before operation or message handling.
16. Layer 6 has exactly these four authority sub-boundaries:
   - frontend entry boundary
   - contract service boundary
   - observability fact/projection boundary
   - product truth boundary
17. Layer 6 explicitly includes:
   - `CreateMeme` as a funding-relevant product entry
   - wallet/provider adapter boundary
   - frontend GraphQL read layer
   - contract `service.rs` query/mutation surface
   - account/application/token identity normalization boundary
   - wallet-type-specific submission capability boundary
   - raw fact ingestion boundary
   - application discovery and registry persistence boundary
   - decoder and registry boundary
   - normalized event family boundary
   - projection and market/funding derivation boundary
   - projection-backed query and serializer boundary
   - debug and diagnostic visibility boundary
18. Layer 7 has exactly these six authority sub-boundaries:
   - runtime capability test boundary
   - base handler and dispatch support test boundary
   - funding contract test boundary
   - contract service test boundary
   - observability fact/projection test boundary
   - frontend funding-entry test boundary
19. Layer 7 explicitly includes:
   - runtime capability baseline tests
   - base handler and dispatch support baseline tests
   - funding contract tests for `swap`, `pool`, `meme`, and `proxy`
   - contract service tests / service-layer baseline tests
   - observability raw ingestion / decoder / normalizer / projection / query / diagnostic baseline tests
   - frontend funding-entry baseline tests
   - frontend funding-entry routing / mode-selection baseline tests
   - frontend funding submission semantics baseline tests
20. Gate 2 is constrained to use these layers in this order.

## Gate 1B In-Scope Files

Gate 2 must audit only the files listed in this section.

### Gate 1B Layer 1 Protocol Definition Files

1. ABI roots:
   - `abi/src/lib.rs`
   - `abi/src/ams.rs`
   - `abi/src/approval.rs`
   - `abi/src/blob_gateway.rs`
   - `abi/src/deposit.rs`
   - `abi/src/hash.rs`
   - `abi/src/meme.rs`
   - `abi/src/policy.rs`
   - `abi/src/proxy.rs`
   - `abi/src/store_type.rs`
2. Swap ABI:
   - `abi/src/swap/mod.rs`
   - `abi/src/swap/router.rs`
   - `abi/src/swap/transaction.rs`
   - `abi/src/swap/pool/mod.rs`
3. Contract-local protocol interfaces:
   - `swap/src/interfaces.rs`
   - `swap/src/interfaces/state.rs`
   - `pool/src/interfaces.rs`
   - `pool/src/interfaces/parameters.rs`
   - `pool/src/interfaces/state.rs`
   - `meme/src/interfaces.rs`
   - `meme/src/interfaces/parameters.rs`
   - `meme/src/interfaces/state.rs`
   - `proxy/src/interfaces.rs`
   - `proxy/src/interfaces/state.rs`

### Gate 1B Layer 2 Runtime Abstraction Files

1. Runtime capability files:
   - `runtime/src/lib.rs`
   - `runtime/src/errors.rs`
   - `runtime/src/contract.rs`
   - `runtime/src/interfaces.rs`
   - `runtime/src/interfaces/access_control.rs`
   - `runtime/src/interfaces/base.rs`
   - `runtime/src/interfaces/contract.rs`
   - `runtime/src/interfaces/meme.rs`
2. Base dispatch support:
   - `base/src/lib.rs`
   - `base/src/handler.rs`
   - `base/src/propose_candidate.rs`

### Gate 1B Layer 3 Contract Dispatch Boundary Files

1. Swap dispatch:
   - `swap/src/contract.rs`
   - `swap/src/contract_impl.rs`
   - `swap/src/contract_inner.rs`
   - `swap/src/lib.rs`
2. Pool dispatch:
   - `pool/src/contract.rs`
   - `pool/src/contract_impl.rs`
   - `pool/src/contract_inner.rs`
   - `pool/src/lib.rs`
3. Meme dispatch:
   - `meme/src/contract.rs`
   - `meme/src/contract_impl.rs`
   - `meme/src/contract_inner.rs`
   - `meme/src/lib.rs`
4. Proxy dispatch:
   - `proxy/src/contract.rs`
   - `proxy/src/contract_impl.rs`
   - `proxy/src/contract_inner.rs`
   - `proxy/src/lib.rs`

### Gate 1B Layer 4 Contract Handler Files

1. Swap handlers:
   - `swap/src/contract_inner/errors.rs`
   - `swap/src/contract_inner/handlers.rs`
   - `swap/src/contract_inner/handlers/create_pool.rs`
   - `swap/src/contract_inner/handlers/operation.rs`
   - `swap/src/contract_inner/handlers/operation/create_pool.rs`
   - `swap/src/contract_inner/handlers/operation/initialize_liquidity.rs`
   - `swap/src/contract_inner/handlers/operation/update_pool.rs`
   - `swap/src/contract_inner/handlers/message.rs`
   - `swap/src/contract_inner/handlers/message/create_pool.rs`
   - `swap/src/contract_inner/handlers/message/create_user_pool.rs`
   - `swap/src/contract_inner/handlers/message/initialize_liquidity.rs`
   - `swap/src/contract_inner/handlers/message/pool_created.rs`
   - `swap/src/contract_inner/handlers/message/update_pool.rs`
   - `swap/src/contract_inner/handlers/message/user_pool_created.rs`
2. Pool handlers:
   - `pool/src/contract_inner/errors.rs`
   - `pool/src/contract_inner/parameters.rs`
   - `pool/src/contract_inner/handlers.rs`
   - `pool/src/contract_inner/handlers/fund_pool_application_creation_chain.rs`
   - `pool/src/contract_inner/handlers/refund.rs`
   - `pool/src/contract_inner/handlers/request_meme_fund.rs`
   - `pool/src/contract_inner/handlers/transfer_meme_from_application.rs`
   - `pool/src/contract_inner/handlers/operation.rs`
   - `pool/src/contract_inner/handlers/operation/add_liquidity.rs`
   - `pool/src/contract_inner/handlers/operation/remove_liquidity.rs`
   - `pool/src/contract_inner/handlers/operation/set_fee_to.rs`
   - `pool/src/contract_inner/handlers/operation/set_fee_to_setter.rs`
   - `pool/src/contract_inner/handlers/operation/swap.rs`
   - `pool/src/contract_inner/handlers/message.rs`
   - `pool/src/contract_inner/handlers/message/add_liquidity.rs`
   - `pool/src/contract_inner/handlers/message/fund_fail.rs`
   - `pool/src/contract_inner/handlers/message/fund_success.rs`
   - `pool/src/contract_inner/handlers/message/new_transaction.rs`
   - `pool/src/contract_inner/handlers/message/remove_liquidity.rs`
   - `pool/src/contract_inner/handlers/message/request_fund.rs`
   - `pool/src/contract_inner/handlers/message/set_fee_to.rs`
   - `pool/src/contract_inner/handlers/message/set_fee_to_setter.rs`
   - `pool/src/contract_inner/handlers/message/swap.rs`
3. Meme handlers:
   - `meme/src/contract_inner/errors.rs`
   - `meme/src/contract_inner/parameters.rs`
   - `meme/src/contract_inner/instantiation_handler.rs`
   - `meme/src/contract_inner/handlers.rs`
   - `meme/src/contract_inner/handlers/open_multi_leader_rounds.rs`
   - `meme/src/contract_inner/handlers/operation.rs`
   - `meme/src/contract_inner/handlers/operation/approve.rs`
   - `meme/src/contract_inner/handlers/operation/creator_chain_id.rs`
   - `meme/src/contract_inner/handlers/operation/initialize_liquidity.rs`
   - `meme/src/contract_inner/handlers/operation/mine.rs`
   - `meme/src/contract_inner/handlers/operation/mint.rs`
   - `meme/src/contract_inner/handlers/operation/redeem.rs`
   - `meme/src/contract_inner/handlers/operation/transfer.rs`
   - `meme/src/contract_inner/handlers/operation/transfer_from.rs`
   - `meme/src/contract_inner/handlers/operation/transfer_from_application.rs`
   - `meme/src/contract_inner/handlers/operation/transfer_ownership.rs`
   - `meme/src/contract_inner/handlers/operation/transfer_to_caller.rs`
   - `meme/src/contract_inner/handlers/message.rs`
   - `meme/src/contract_inner/handlers/message/approve.rs`
   - `meme/src/contract_inner/handlers/message/initialize_liquidity.rs`
   - `meme/src/contract_inner/handlers/message/liquidity_funded.rs`
   - `meme/src/contract_inner/handlers/message/mint.rs`
   - `meme/src/contract_inner/handlers/message/redeem.rs`
   - `meme/src/contract_inner/handlers/message/transfer.rs`
   - `meme/src/contract_inner/handlers/message/transfer_from.rs`
   - `meme/src/contract_inner/handlers/message/transfer_from_application.rs`
   - `meme/src/contract_inner/handlers/message/transfer_ownership.rs`
4. Proxy handlers:
   - `proxy/src/contract_inner/errors.rs`
   - `proxy/src/contract_inner/handlers.rs`
   - `proxy/src/contract_inner/handlers/operation.rs`
   - `proxy/src/contract_inner/handlers/operation/approve_add_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/operation/approve_add_operator.rs`
   - `proxy/src/contract_inner/handlers/operation/approve_ban_operator.rs`
   - `proxy/src/contract_inner/handlers/operation/approve_remove_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/operation/create_meme.rs`
   - `proxy/src/contract_inner/handlers/operation/deregister_miner.rs`
   - `proxy/src/contract_inner/handlers/operation/propose_add_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/operation/propose_add_operator.rs`
   - `proxy/src/contract_inner/handlers/operation/propose_ban_operator.rs`
   - `proxy/src/contract_inner/handlers/operation/propose_remove_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/operation/register_miner.rs`
   - `proxy/src/contract_inner/handlers/message.rs`
   - `proxy/src/contract_inner/handlers/message/approve_add_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/message/approve_add_operator.rs`
   - `proxy/src/contract_inner/handlers/message/approve_ban_operator.rs`
   - `proxy/src/contract_inner/handlers/message/approve_remove_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/message/create_meme.rs`
   - `proxy/src/contract_inner/handlers/message/create_meme_ext.rs`
   - `proxy/src/contract_inner/handlers/message/deregister_miner.rs`
   - `proxy/src/contract_inner/handlers/message/meme_created.rs`
   - `proxy/src/contract_inner/handlers/message/propose_add_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/message/propose_add_operator.rs`
   - `proxy/src/contract_inner/handlers/message/propose_ban_operator.rs`
   - `proxy/src/contract_inner/handlers/message/propose_remove_genesis_miner.rs`
   - `proxy/src/contract_inner/handlers/message/register_miner.rs`

### Gate 1B Layer 5 Persistent State Files

1. Swap state:
   - `swap/src/state.rs`
   - `swap/src/state/adapter.rs`
   - `swap/src/state/errors.rs`
   - `swap/src/state/state_impl.rs`
2. Pool state:
   - `pool/src/state.rs`
   - `pool/src/state/adapter.rs`
   - `pool/src/state/errors.rs`
   - `pool/src/state/state_impl.rs`
3. Meme state:
   - `meme/src/state.rs`
   - `meme/src/state/adapter.rs`
   - `meme/src/state/errors.rs`
   - `meme/src/state/state_impl.rs`
4. Proxy state:
   - `proxy/src/state.rs`
   - `proxy/src/state/adapter.rs`
   - `proxy/src/state/errors.rs`
   - `proxy/src/state/state_impl.rs`

### Gate 1B Layer 6 Product Entry And Truth Boundary Files

1. Contract service files:
   - `swap/src/service.rs`
   - `pool/src/service.rs`
   - `meme/src/service.rs`
   - `proxy/src/service.rs`
2. Frontend page and component entries:
   - `webui-v2/src/layouts/MainLayout.vue`
   - `webui-v2/src/pages/AddLiquidityPage.vue`
   - `webui-v2/src/pages/ExplorePage.vue`
   - `webui-v2/src/pages/PositionsPage.vue`
   - `webui-v2/src/pages/RemoveLiquidityPage.vue`
   - `webui-v2/src/pages/SwapPage.vue`
   - `webui-v2/src/pages/TrendingPage.vue`
   - `webui-v2/src/components/bulletin/BulletinItem.ts`
   - `webui-v2/src/components/bulletin/BulletinListItemView.vue`
   - `webui-v2/src/components/bulletin/BulletinListView.vue`
   - `webui-v2/src/components/common/SectionTitleView.vue`
   - `webui-v2/src/components/footer/FooterView.vue`
   - `webui-v2/src/components/header/HeaderView.vue`
   - `webui-v2/src/components/header/NetworkView.vue`
   - `webui-v2/src/components/header/TabsView.vue`
   - `webui-v2/src/components/logo/LogoView.vue`
   - `webui-v2/src/components/meme/CreateMemeBtn.vue`
   - `webui-v2/src/components/meme/CreateMemeView.vue`
   - `webui-v2/src/components/pools/poolFlow.ts`
   - `webui-v2/src/components/pools/PoolLogoView.vue`
   - `webui-v2/src/components/pools/PoolPairLogo.vue`
   - `webui-v2/src/components/protocol/ProtocolInfoView.vue`
   - `webui-v2/src/components/search/SearchView.vue`
   - `webui-v2/src/components/subscription/ApplicationsView.vue`
   - `webui-v2/src/components/subscription/BlobsView.vue`
   - `webui-v2/src/components/subscription/MemesView.vue`
   - `webui-v2/src/components/subscription/PoolsView.vue`
   - `webui-v2/src/components/subscription/SubscriptionView.vue`
   - `webui-v2/src/components/subscription/WalletView.vue`
   - `webui-v2/src/components/tokens/PoolsListView.vue`
   - `webui-v2/src/components/tokens/Tab.ts`
   - `webui-v2/src/components/tokens/TokensListView.vue`
   - `webui-v2/src/components/tokens/TokensPanelView.vue`
   - `webui-v2/src/components/tokens/TransactionsListView.vue`
   - `webui-v2/src/components/tokens/VolumeSelectView.vue`
   - `webui-v2/src/components/trade/SetSlippageView.vue`
   - `webui-v2/src/components/trade/Slippages.ts`
   - `webui-v2/src/components/trade/Token.ts`
   - `webui-v2/src/components/trade/TokenAction.ts`
   - `webui-v2/src/components/trade/TokenInfoLineView.vue`
   - `webui-v2/src/components/trade/TokenInfoView.vue`
   - `webui-v2/src/components/trade/TokenInputView.vue`
   - `webui-v2/src/components/trade/TradeDetailView.vue`
   - `webui-v2/src/components/trade/TradeInfoView.vue`
   - `webui-v2/src/components/trade/TradeView.vue`
   - `webui-v2/src/components/trending/trendingData.ts`
   - `webui-v2/src/components/trending/TrendingView.vue`
3. Frontend route, store, request, wallet, and protocol utility files:
   - `webui-v2/src/router/index.ts`
   - `webui-v2/src/router/routes.ts`
   - `webui-v2/src/apollo/apollo-client-config.js`
   - `webui-v2/src/apollo/apollo-client-hooks.js`
   - `webui-v2/src/apollo/apollo-provider-hooks.js`
   - `webui-v2/src/apollo/client.ts`
   - `webui-v2/src/apollo/index.ts`
   - `webui-v2/src/constant/const.ts`
   - `webui-v2/src/constant/domain.ts`
   - `webui-v2/src/constant/index.ts`
   - `webui-v2/src/components/wallet/ConnectWalletBtn.vue`
   - `webui-v2/src/components/wallet/ConnectWalletView.vue`
   - `webui-v2/src/components/wallet/WalletInfoMenuView.vue`
   - `webui-v2/src/components/wallet/WalletInfoView.vue`
   - `webui-v2/src/components/wallet/WalletSwitchMenuView.vue`
   - `webui-v2/src/components/wallet/WalletTipView.vue`
   - `webui-v2/src/stores/index.ts`
   - `webui-v2/src/stores/export.ts`
   - `webui-v2/src/stores/account/index.ts`
   - `webui-v2/src/stores/account/types.ts`
   - `webui-v2/src/stores/ams/index.ts`
   - `webui-v2/src/stores/ams/pagination.ts`
   - `webui-v2/src/stores/ams/store.ts`
   - `webui-v2/src/stores/ams/types.ts`
   - `webui-v2/src/stores/ams/wrapper.ts`
   - `webui-v2/src/stores/blob/index.ts`
   - `webui-v2/src/stores/blob/store.ts`
   - `webui-v2/src/stores/blob/types.ts`
   - `webui-v2/src/stores/blob/wrapper.ts`
   - `webui-v2/src/stores/meme/index.ts`
   - `webui-v2/src/stores/meme/store.ts`
   - `webui-v2/src/stores/meme/types.ts`
   - `webui-v2/src/stores/meme/wrapper.ts`
   - `webui-v2/src/stores/notify/const.ts`
   - `webui-v2/src/stores/notify/helper.ts`
   - `webui-v2/src/stores/notify/index.ts`
   - `webui-v2/src/stores/notify/store.ts`
   - `webui-v2/src/stores/notify/types.ts`
   - `webui-v2/src/stores/notify/wrapper.ts`
   - `webui-v2/src/stores/pool/index.ts`
   - `webui-v2/src/stores/pool/store.ts`
   - `webui-v2/src/stores/pool/types.ts`
   - `webui-v2/src/stores/pool/wrapper.ts`
   - `webui-v2/src/stores/positions/index.ts`
   - `webui-v2/src/stores/positions/store.ts`
   - `webui-v2/src/stores/positions/types.ts`
   - `webui-v2/src/stores/positions/wrapper.ts`
   - `webui-v2/src/stores/proxy/index.ts`
   - `webui-v2/src/stores/proxy/store.ts`
   - `webui-v2/src/stores/proxy/types.ts`
   - `webui-v2/src/stores/proxy/wrapper.ts`
   - `webui-v2/src/stores/request/action.ts`
   - `webui-v2/src/stores/request/index.ts`
   - `webui-v2/src/stores/request/types.ts`
   - `webui-v2/src/stores/request/axiosapi/axios.ts`
   - `webui-v2/src/stores/request/axiosapi/index.ts`
   - `webui-v2/src/stores/swap/index.ts`
   - `webui-v2/src/stores/swap/poolIdentity.ts`
   - `webui-v2/src/stores/swap/store.ts`
   - `webui-v2/src/stores/swap/types.ts`
   - `webui-v2/src/stores/swap/wrapper.ts`
   - `webui-v2/src/stores/store/index.ts`
   - `webui-v2/src/stores/store/types.ts`
   - `webui-v2/src/stores/transaction/index.ts`
   - `webui-v2/src/stores/transaction/types.ts`
   - `webui-v2/src/stores/user/index.ts`
   - `webui-v2/src/stores/user/store.ts`
   - `webui-v2/src/stores/user/types.ts`
   - `webui-v2/src/stores/user/wrapper.ts`
   - `webui-v2/src/model/index.ts`
   - `webui-v2/src/model/db/model.ts`
   - `webui-v2/src/model/rpc/model.ts`
   - `webui-v2/src/utils/creator_chain_id.ts`
   - `webui-v2/src/utils/graphql_result.ts`
   - `webui-v2/src/utils/hex.ts`
   - `webui-v2/src/utils/index.ts`
   - `webui-v2/src/utils/protocol.ts`
   - `webui-v2/src/utils/seo.ts`
   - `webui-v2/src/wallet/checko.ts`
   - `webui-v2/src/wallet/index.ts`
   - `webui-v2/src/wallet/linera_web_client.ts`
   - `webui-v2/src/wallet/provider.ts`
   - `webui-v2/src/wallet/wallet.ts`
   - `webui-v2/src/window.d.ts`
4. Frontend operation serialization files:
   - `webui-v2/wasm/src/lib.rs`
   - `webui-v2/wasm/src/fake_pool.rs`
   - `webui-v2/wasm/src/fake_proxy.rs`
   - `webui-v2/wasm/src/fake_swap.rs`
5. Frontend GraphQL declaration files:
   - `webui-v2/src/graphql/index.ts`
   - `webui-v2/src/graphql/ams.ts`
   - `webui-v2/src/graphql/application_raw.ts`
   - `webui-v2/src/graphql/blob.ts`
   - `webui-v2/src/graphql/meme_raw.ts`
   - `webui-v2/src/graphql/pool_raw.ts`
   - `webui-v2/src/graphql/proxy.ts`
   - `webui-v2/src/graphql/proxy_raw.ts`
   - `webui-v2/src/graphql/service.ts`
   - `webui-v2/src/graphql/service_raw.ts`
   - `webui-v2/src/graphql/swap.ts`
   - `webui-v2/src/graphql/swap_raw.ts`
6. Frontend projection transport and worker files:
   - `webui-v2/src/bridge/db/index.ts`
   - `webui-v2/src/bridge/db/kline.ts`
   - `webui-v2/src/bridge/db/klineCacheCompatibility.ts`
   - `webui-v2/src/bridge/db/transaction.ts`
   - `webui-v2/src/bridge/index.ts`
   - `webui-v2/src/components/kline/ChartSettings.vue`
   - `webui-v2/src/components/kline/ChartToolbar.vue`
   - `webui-v2/src/components/kline/ChartType.ts`
   - `webui-v2/src/components/kline/ChartTypeSelector.vue`
   - `webui-v2/src/components/kline/IndicatorSelector.vue`
   - `webui-v2/src/components/kline/IntervalSelectorDropdown.vue`
   - `webui-v2/src/components/kline/IntervalSelectorView.vue`
   - `webui-v2/src/components/kline/PriceChartView.vue`
   - `webui-v2/src/components/kline/chart/ChartView.vue`
   - `webui-v2/src/components/kline/chart/KlineData.ts`
   - `webui-v2/src/components/kline/chart/chartDataUpdate.ts`
   - `webui-v2/src/components/kline/chart/indicatorRenderScheduler.ts`
   - `webui-v2/src/components/kline/chart/visibleRangeLoad.ts`
   - `webui-v2/src/components/kline/loadQueue.ts`
   - `webui-v2/src/components/kline/priceChartMemorySnapshots.ts`
   - `webui-v2/src/components/kline/priceChartPointState.ts`
   - `webui-v2/src/components/kline/priceChartStartup.ts`
   - `webui-v2/src/components/kline/startupBaseline.ts`
   - `webui-v2/src/components/kline/startupInstrumentation.ts`
   - `webui-v2/src/controller/clientMigrations.ts`
   - `webui-v2/src/controller/db.ts`
   - `webui-v2/src/controller/index.ts`
   - `webui-v2/src/stores/kline/const.ts`
   - `webui-v2/src/stores/kline/index.ts`
   - `webui-v2/src/stores/kline/liveUpdate.ts`
   - `webui-v2/src/stores/kline/pointOverwrite.ts`
   - `webui-v2/src/stores/kline/poolStats.ts`
   - `webui-v2/src/stores/kline/store.ts`
   - `webui-v2/src/stores/kline/types.ts`
   - `webui-v2/src/stores/kline/wrapper.ts`
   - `webui-v2/src/subscription/index.ts`
   - `webui-v2/src/subscription/subscription.ts`
   - `webui-v2/src/websocket/index.ts`
   - `webui-v2/src/websocket/websocket.ts`
   - `webui-v2/src/worker/kline/index.ts`
   - `webui-v2/src/worker/kline/kline.ts`
   - `webui-v2/src/worker/kline/listenerRegistry.ts`
   - `webui-v2/src/worker/kline/pointMerge.ts`
   - `webui-v2/src/worker/kline/runner.ts`
   - `webui-v2/src/worker/kline/worker.ts`
7. Observability application and lifecycle files:
   - `service/kline/src/app/bootstrap.py`
   - `service/kline/src/app/config.py`
   - `service/kline/src/app/lifecycle.py`
   - `service/kline/src/app/observability_facade.py`
   - `service/kline/src/app/observability_runtime.py`
   - `service/kline/src/app/observability_status.py`
   - `service/kline/src/app/observability_supervisor.py`
   - `service/kline/src/kline.py`
   - `service/kline/src/kline_runtime.py`
   - `service/kline/src/kline_service_lifecycle.py`
8. Observability ingestion, registry, normalization, projection, market, query, realtime, and storage files:
   - `service/kline/src/ingestion/__init__.py`
   - `service/kline/src/ingestion/anomalies.py`
   - `service/kline/src/ingestion/block_parser.py`
   - `service/kline/src/ingestion/catch_up_driver.py`
   - `service/kline/src/ingestion/catch_up_runner.py`
   - `service/kline/src/ingestion/chain_cursor_store.py`
   - `service/kline/src/ingestion/chain_event_processor.py`
   - `service/kline/src/ingestion/coordinator.py`
   - `service/kline/src/ingestion/cursors.py`
   - `service/kline/src/ingestion/post_ingest_pipeline.py`
   - `service/kline/src/integration/__init__.py`
   - `service/kline/src/integration/block_not_available_error.py`
   - `service/kline/src/integration/chain_client.py`
   - `service/kline/src/integration/linera_graphql_chain_client.py`
   - `service/kline/src/integration/linera_graphql_notification_listener.py`
   - `service/kline/src/integration/pool_application_client.py`
   - `service/kline/src/integration/proxy_catalog_client.py`
   - `service/kline/src/integration/swap_catalog_client.py`
   - `service/kline/src/market/market_derivation_replay_driver.py`
   - `service/kline/src/market/market_derivation_worker.py`
   - `service/kline/src/market/pool_executed_event_payload.py`
   - `service/kline/src/market/pool_new_transaction_execution_fact.py`
   - `service/kline/src/market/pool_new_transaction_execution_fact_extractor.py`
   - `service/kline/src/market/position_metrics_protocol_fee_ownership_tracker.py`
   - `service/kline/src/market/position_metrics_snapshot_builder.py`
   - `service/kline/src/market/position_metrics_snapshot_materializer.py`
   - `service/kline/src/market/position_metrics_snapshot_principal_simulator.py`
   - `service/kline/src/market/settled_market_deriver.py`
   - `service/kline/src/market/settled_market_materializer.py`
   - `service/kline/src/market/settled_market_result.py`
   - `service/kline/src/market/settled_output_batch.py`
   - `service/kline/src/market/settled_output_batch_factory.py`
   - `service/kline/src/normalizer/__init__.py`
   - `service/kline/src/normalizer/application_event_family_resolver.py`
   - `service/kline/src/normalizer/decode_result_normalizer.py`
   - `service/kline/src/normalizer/normalization_replay_driver.py`
   - `service/kline/src/normalizer/normalization_worker.py`
   - `service/kline/src/normalizer/normalized_event_materializer.py`
   - `service/kline/src/normalizer/normalized_event_result.py`
   - `service/kline/src/normalizer/pool_catalog_projection_materializer.py`
   - `service/kline/src/normalizer/pool_executed_event_shape_validator.py`
   - `service/kline/src/projection/__init__.py`
   - `service/kline/src/projection/candles/__init__.py`
   - `service/kline/src/projection/pools/__init__.py`
   - `service/kline/src/projection/positions/__init__.py`
   - `service/kline/src/projection/projector.py`
   - `service/kline/src/projection/trades/__init__.py`
   - `service/kline/src/query/__init__.py`
   - `service/kline/src/query/handlers/__init__.py`
   - `service/kline/src/query/handlers/kline.py`
   - `service/kline/src/query/handlers/position_metrics.py`
   - `service/kline/src/query/handlers/position_metrics_noop_diagnostic_recorder.py`
   - `service/kline/src/query/handlers/positions.py`
   - `service/kline/src/query/handlers/transactions.py`
   - `service/kline/src/query/read_models/__init__.py`
   - `service/kline/src/query/read_models/candles.py`
   - `service/kline/src/query/read_models/position_metrics.py`
   - `service/kline/src/query/read_models/position_metrics_fast_path_executor.py`
   - `service/kline/src/query/read_models/position_metrics_fast_path_plan_builder.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_context.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_coordinator.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_inputs.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_plan.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_reason_code.py`
   - `service/kline/src/query/read_models/position_metrics_fetch_stage.py`
   - `service/kline/src/query/read_models/position_metrics_fetched_result.py`
   - `service/kline/src/query/read_models/position_metrics_payload_only_executor.py`
   - `service/kline/src/query/read_models/position_metrics_pool_state_snapshot.py`
   - `service/kline/src/query/read_models/position_metrics_position_basis_snapshot.py`
   - `service/kline/src/query/read_models/position_metrics_product_state_query_input_provider.py`
   - `service/kline/src/query/read_models/position_metrics_projection_payload_adapter.py`
   - `service/kline/src/query/read_models/position_metrics_protocol_fee_split_semantics.py`
   - `service/kline/src/query/read_models/position_metrics_read_result.py`
   - `service/kline/src/query/read_models/position_metrics_replay_bundle.py`
   - `service/kline/src/query/read_models/position_metrics_replay_facts.py`
   - `service/kline/src/query/read_models/position_metrics_replay_fallback_executor.py`
   - `service/kline/src/query/read_models/position_metrics_replay_fallback_result_builder.py`
   - `service/kline/src/query/read_models/position_metrics_replay_snapshot_shadow_builder.py`
   - `service/kline/src/query/read_models/position_metrics_replay_summary.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_fast_path.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_fast_path_eligibility.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_fast_path_exact_case_resolver.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_fast_path_result_builder.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_inputs.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_semantic_facts.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_shadow_evaluator.py`
   - `service/kline/src/query/read_models/position_metrics_snapshot_shadow_payload_builder.py`
   - `service/kline/src/query/read_models/positions.py`
   - `service/kline/src/query/read_models/transactions.py`
   - `service/kline/src/query/read_models/virtual_positions.py`
   - `service/kline/src/query/serializers/__init__.py`
   - `service/kline/src/query/serializers/kline.py`
   - `service/kline/src/query/serializers/positions.py`
   - `service/kline/src/query/serializers/transactions.py`
   - `service/kline/src/realtime/__init__.py`
   - `service/kline/src/realtime/candle_finality_scheduler.py`
   - `service/kline/src/realtime/market_data_event.py`
   - `service/kline/src/realtime/market_data_event_publisher.py`
   - `service/kline/src/realtime/market_data_event_queue.py`
   - `service/kline/src/realtime/market_data_event_sink.py`
   - `service/kline/src/realtime/market_data_payload_builder.py`
   - `service/kline/src/realtime/realtime_diagnostic_recorder.py`
   - `service/kline/src/registry/ams_message_decoder.py`
   - `service/kline/src/registry/ams_operation_decoder.py`
   - `service/kline/src/registry/application_discovery_service.py`
   - `service/kline/src/registry/application_registry.py`
   - `service/kline/src/registry/blob_gateway_message_decoder.py`
   - `service/kline/src/registry/blob_gateway_operation_decoder.py`
   - `service/kline/src/registry/decode_dispatch_result.py`
   - `service/kline/src/registry/decode_scheduler.py`
   - `service/kline/src/registry/decoded_transaction_payload_normalizer.py`
   - `service/kline/src/registry/decoder_dispatcher.py`
   - `service/kline/src/registry/decoder_registry.py`
   - `service/kline/src/registry/meme_message_decoder.py`
   - `service/kline/src/registry/meme_operation_decoder.py`
   - `service/kline/src/registry/pool_event_decoder.py`
   - `service/kline/src/registry/pool_message_decoder.py`
   - `service/kline/src/registry/pool_operation_decoder.py`
   - `service/kline/src/registry/proxy_message_decoder.py`
   - `service/kline/src/registry/proxy_operation_decoder.py`
   - `service/kline/src/registry/rust_decoder_runner.py`
   - `service/kline/src/registry/swap_message_decoder.py`
   - `service/kline/src/registry/swap_operation_decoder.py`
   - `service/kline/src/storage/mysql/__init__.py`
   - `service/kline/src/storage/mysql/application_registry_repo.py`
   - `service/kline/src/storage/mysql/canonical_fingerprint.py`
   - `service/kline/src/storage/mysql/connection.py`
   - `service/kline/src/storage/mysql/debug_traces_query_repo.py`
   - `service/kline/src/storage/mysql/diagnostic_events_query_repo.py`
   - `service/kline/src/storage/mysql/maker_events_query_repo.py`
   - `service/kline/src/storage/mysql/market_stats_projection_repo.py`
   - `service/kline/src/storage/mysql/normalized_repo.py`
   - `service/kline/src/storage/mysql/pool_catalog_projection_repo.py`
   - `service/kline/src/storage/mysql/pool_catalog_query_repo.py`
   - `service/kline/src/storage/mysql/pool_identity_projection_repo.py`
   - `service/kline/src/storage/mysql/pool_metadata_projection_resolver.py`
   - `service/kline/src/storage/mysql/pool_state_projection_repo.py`
   - `service/kline/src/storage/mysql/pool_state_snapshot_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_diagnostic_recorder.py`
   - `service/kline/src/storage/mysql/position_metrics_positions_projection_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_replay_facts_projection_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_snapshot_inputs_projection_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_snapshot_materialization_inputs_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_snapshot_projection_repo.py`
   - `service/kline/src/storage/mysql/position_metrics_snapshot_semantic_facts_projector.py`
   - `service/kline/src/storage/mysql/position_state_projection_repo.py`
   - `service/kline/src/storage/mysql/position_state_snapshot_repo.py`
   - `service/kline/src/storage/mysql/processing_cursor_repo.py`
   - `service/kline/src/storage/mysql/projection_pool_catalog_repo.py`
   - `service/kline/src/storage/mysql/projection_query_unavailable_error.py`
   - `service/kline/src/storage/mysql/raw_repo.py`
   - `service/kline/src/storage/mysql/repository_connection_mixin.py`
   - `service/kline/src/storage/mysql/settled_liquidity_change_repo.py`
   - `service/kline/src/storage/mysql/settled_liquidity_projection_repo.py`
   - `service/kline/src/storage/mysql/settled_pool_history_projection_repo.py`
   - `service/kline/src/storage/mysql/settled_product_transaction_adapter.py`
   - `service/kline/src/storage/mysql/settled_trade_projection_repo.py`
   - `service/kline/src/storage/mysql/settled_trade_repo.py`
   - `service/kline/src/storage/mysql/transaction_watermarks_query_repo.py`
9. Observability entry and diagnostic files:
   - `service/kline/src/account_codec.py`
   - `service/kline/src/async_request.py`
   - `service/kline/src/db.py`
   - `service/kline/src/kline_debug_service.py`
   - `service/kline/src/kline_entrypoint_services.py`
   - `service/kline/src/kline_observability_debug_service.py`
   - `service/kline/src/kline_position_metrics_debug_service.py`
   - `service/kline/src/kline_position_metrics_dependencies.py`
   - `service/kline/src/position_metrics_bootstrap.py`
   - `service/kline/src/position_metrics_entrypoint.py`
   - `service/kline/src/position_metrics_estimated_fallback_resolver.py`
   - `service/kline/src/position_metrics_fee_free_open_state_simulator.py`
   - `service/kline/src/position_metrics_fee_to_opening_mint_resolver.py`
   - `service/kline/src/position_metrics_history_enricher.py`
   - `service/kline/src/position_metrics_history_evaluation.py`
   - `service/kline/src/position_metrics_history_semantic_resolver.py`
   - `service/kline/src/position_metrics_liquidity_history_analyzer.py`
   - `service/kline/src/position_metrics_no_swap_exact_resolver.py`
   - `service/kline/src/position_metrics_partial_result_builder.py`
   - `service/kline/src/position_metrics_payload_decision.py`
   - `service/kline/src/position_metrics_payload_decision_resolver.py`
   - `service/kline/src/position_metrics_payload_decision_result.py`
   - `service/kline/src/position_metrics_payload_enricher.py`
   - `service/kline/src/position_metrics_payload_planner.py`
   - `service/kline/src/position_metrics_payload_result.py`
   - `service/kline/src/position_metrics_payload_semantic_builder.py`
   - `service/kline/src/position_metrics_pool_application_payload_api.py`
   - `service/kline/src/position_metrics_pool_application_payload_fetcher.py`
   - `service/kline/src/position_metrics_pool_history_reconstructor.py`
   - `service/kline/src/position_metrics_pool_history_replay_inspector.py`
   - `service/kline/src/position_metrics_public_api.py`
   - `service/kline/src/position_metrics_replay_entrypoint.py`
   - `service/kline/src/position_metrics_swap_history_alignment_checker.py`
   - `service/kline/src/position_metrics_swap_history_exact_materializer.py`
   - `service/kline/src/position_metrics_swap_history_exactness_solver.py`
   - `service/kline/src/position_metrics_swap_history_exactness_validator.py`
   - `service/kline/src/position_metrics_swap_history_precheck.py`
   - `service/kline/src/position_metrics_swap_math_support.py`
   - `service/kline/src/position_metrics_value_support.py`
   - `service/kline/src/position_metrics_warning_applier.py`
   - `service/kline/src/request_trace.py`
   - `service/kline/src/subscription.py`
   - `service/kline/src/transaction_family_codec.py`

### Gate 1B Layer 7 Test Baseline Files

1. Runtime, base, ABI, and contract test files:
   - No `runtime/src/**/*test*.rs`, `runtime/tests/**/*.rs`, `base/src/**/*test*.rs`, or `base/tests/**/*.rs` file exists at Gate 1B review time.
   - `abi/src/meme_tests.rs`
   - `swap/src/contract_tests.rs`
   - `swap/src/contract_tests/contract.rs`
   - `swap/tests/kline_e2e.rs`
   - `swap/tests/meme_meme_pair.rs`
   - `swap/tests/meme_native_pair_mining_full_supply.rs`
   - `swap/tests/meme_native_pair_mining_part_supply.rs`
   - `swap/tests/meme_native_pair_no_mining.rs`
   - `swap/tests/meme_native_pair_without_initial_liquidity.rs`
   - `pool/src/contract_tests.rs`
   - `pool/src/contract_tests/contract.rs`
   - `pool/tests/meme_meme_pair.rs`
   - `pool/tests/meme_native_create_pool.rs`
   - `pool/tests/meme_native_pool.rs`
   - `pool/tests/panic_creator_rug.rs`
   - `meme/src/contract_tests.rs`
   - `meme/src/contract_tests/contract.rs`
   - `meme/src/contract_tests/crash.rs`
   - `meme/src/service_tests.rs`
   - `meme/src/service_tests/service.rs`
   - `meme/tests/meme_mining_full_supply.rs`
   - `meme/tests/meme_mining_part_supply.rs`
   - `meme/tests/meme_no_mining.rs`
   - `meme/tests/test_suite.rs`
   - `proxy/src/contract_tests.rs`
   - `proxy/src/contract_tests/contract.rs`
   - `proxy/src/service_tests.rs`
   - `proxy/src/service_tests/service.rs`
   - `proxy/tests/multi_owner.rs`
   - `proxy/tests/single_owner_real.rs`
   - `proxy/tests/single_owner_virtual.rs`
   - `proxy/tests/suite.rs`
2. Kline test files:
   - `service/kline/tests/account_codec_test.py`
   - `service/kline/tests/app_bootstrap_test.py`
   - `service/kline/tests/application_discovery_service_test.py`
   - `service/kline/tests/application_registry_repo_test.py`
   - `service/kline/tests/application_registry_test.py`
   - `service/kline/tests/async_request_test.py`
   - `service/kline/tests/block_parser_test.py`
   - `service/kline/tests/candle_finality_scheduler_test.py`
   - `service/kline/tests/candle_schema_test.py`
   - `service/kline/tests/canonical_fingerprint_test.py`
   - `service/kline/tests/catch_up_driver_test.py`
   - `service/kline/tests/catch_up_runner_test.py`
   - `service/kline/tests/chain_cursor_store_test.py`
   - `service/kline/tests/chain_event_processor_test.py`
   - `service/kline/tests/conftest.py`
   - `service/kline/tests/db_test.py`
   - `service/kline/tests/decode_result_normalizer_test.py`
   - `service/kline/tests/decode_scheduler_test.py`
   - `service/kline/tests/decoder_dispatcher_test.py`
   - `service/kline/tests/decoder_registry_test.py`
   - `service/kline/tests/ingestion_coordinator_test.py`
   - `service/kline/tests/kline_position_metrics_dependencies_test.py`
   - `service/kline/tests/kline_runtime_test.py`
   - `service/kline/tests/kline_service_lifecycle_test.py`
   - `service/kline/tests/linera_graphql_chain_client_test.py`
   - `service/kline/tests/linera_graphql_notification_listener_test.py`
   - `service/kline/tests/maker_api_test.py`
   - `service/kline/tests/maker_execution_policy_test.py`
   - `service/kline/tests/maker_inventory_controller_test.py`
   - `service/kline/tests/maker_minute_plan_test.py`
   - `service/kline/tests/maker_minute_scheduler_test.py`
   - `service/kline/tests/maker_reference_price_engine_test.py`
   - `service/kline/tests/maker_simulation_test.py`
   - `service/kline/tests/market_data_event_publisher_test.py`
   - `service/kline/tests/market_data_event_queue_test.py`
   - `service/kline/tests/market_data_event_sink_test.py`
   - `service/kline/tests/market_derivation_replay_driver_test.py`
   - `service/kline/tests/market_derivation_worker_test.py`
   - `service/kline/tests/market_stats_projection_repo_test.py`
   - `service/kline/tests/message_decoder_registration_test.py`
   - `service/kline/tests/normalization_replay_driver_test.py`
   - `service/kline/tests/normalization_worker_test.py`
   - `service/kline/tests/normalized_event_materializer_test.py`
   - `service/kline/tests/normalized_repo_test.py`
   - `service/kline/tests/observability_e2e_test.sh`
   - `service/kline/tests/observability_reconciliation_test.py`
   - `service/kline/tests/pool_application_client_test.py`
   - `service/kline/tests/pool_catalog_projection_repo_test.py`
   - `service/kline/tests/pool_decoder_test.py`
   - `service/kline/tests/pool_executed_event_payload_test.py`
   - `service/kline/tests/pool_executed_event_shape_validator_test.py`
   - `service/kline/tests/pool_identity_projection_repo_test.py`
   - `service/kline/tests/pool_new_transaction_execution_fact_extractor_test.py`
   - `service/kline/tests/pool_state_projection_repo_test.py`
   - `service/kline/tests/pool_state_snapshot_repo_test.py`
   - `service/kline/tests/position_metrics_bootstrap_test.py`
   - `service/kline/tests/position_metrics_entrypoint_test.py`
   - `service/kline/tests/position_metrics_estimated_fallback_resolver_test.py`
   - `service/kline/tests/position_metrics_fast_path_executor_test.py`
   - `service/kline/tests/position_metrics_fast_path_plan_builder_test.py`
   - `service/kline/tests/position_metrics_fee_free_open_state_simulator_test.py`
   - `service/kline/tests/position_metrics_fee_to_opening_mint_resolver_test.py`
   - `service/kline/tests/position_metrics_fetch_context_test.py`
   - `service/kline/tests/position_metrics_fetch_coordinator_test.py`
   - `service/kline/tests/position_metrics_fetch_inputs_test.py`
   - `service/kline/tests/position_metrics_fetch_plan_test.py`
   - `service/kline/tests/position_metrics_fetched_result_test.py`
   - `service/kline/tests/position_metrics_history_enricher_test.py`
   - `service/kline/tests/position_metrics_history_semantic_resolver_test.py`
   - `service/kline/tests/position_metrics_liquidity_history_analyzer_test.py`
   - `service/kline/tests/position_metrics_no_swap_exact_resolver_test.py`
   - `service/kline/tests/position_metrics_partial_result_builder_test.py`
   - `service/kline/tests/position_metrics_payload_decision_resolver_test.py`
   - `service/kline/tests/position_metrics_payload_only_executor_test.py`
   - `service/kline/tests/position_metrics_payload_planner_test.py`
   - `service/kline/tests/position_metrics_payload_semantic_builder_test.py`
   - `service/kline/tests/position_metrics_pool_application_payload_fetcher_test.py`
   - `service/kline/tests/position_metrics_pool_history_reconstructor_test.py`
   - `service/kline/tests/position_metrics_pool_history_replay_inspector_test.py`
   - `service/kline/tests/position_metrics_pool_state_snapshot_test.py`
   - `service/kline/tests/position_metrics_position_basis_snapshot_test.py`
   - `service/kline/tests/position_metrics_protocol_fee_ownership_tracker_test.py`
   - `service/kline/tests/position_metrics_public_api_test.py`
   - `service/kline/tests/position_metrics_query_input_provider_test.py`
   - `service/kline/tests/position_metrics_read_result_test.py`
   - `service/kline/tests/position_metrics_replay_entrypoint_test.py`
   - `service/kline/tests/position_metrics_replay_facts_projection_repo_test.py`
   - `service/kline/tests/position_metrics_replay_facts_test.py`
   - `service/kline/tests/position_metrics_replay_fallback_executor_test.py`
   - `service/kline/tests/position_metrics_replay_fallback_result_builder_test.py`
   - `service/kline/tests/position_metrics_replay_snapshot_shadow_builder_test.py`
   - `service/kline/tests/position_metrics_replay_summary_test.py`
   - `service/kline/tests/position_metrics_snapshot_builder_test.py`
   - `service/kline/tests/position_metrics_snapshot_fast_path_exact_case_resolver_test.py`
   - `service/kline/tests/position_metrics_snapshot_materialization_inputs_repo_test.py`
   - `service/kline/tests/position_metrics_snapshot_materializer_test.py`
   - `service/kline/tests/position_metrics_snapshot_principal_simulator_test.py`
   - `service/kline/tests/position_metrics_snapshot_projection_repo_test.py`
   - `service/kline/tests/position_metrics_snapshot_semantic_facts_test.py`
   - `service/kline/tests/position_metrics_snapshot_shadow_payload_builder_test.py`
   - `service/kline/tests/position_metrics_swap_history_alignment_checker_test.py`
   - `service/kline/tests/position_metrics_swap_history_exact_materializer_test.py`
   - `service/kline/tests/position_metrics_swap_history_exactness_solver_test.py`
   - `service/kline/tests/position_metrics_swap_history_exactness_validator_test.py`
   - `service/kline/tests/position_metrics_swap_history_precheck_test.py`
   - `service/kline/tests/position_metrics_swap_math_support_test.py`
   - `service/kline/tests/position_metrics_test.py`
   - `service/kline/tests/position_metrics_warning_applier_test.py`
   - `service/kline/tests/position_state_projection_repo_test.py`
   - `service/kline/tests/position_state_snapshot_repo_test.py`
   - `service/kline/tests/positions_api_test.py`
   - `service/kline/tests/post_ingest_pipeline_test.py`
   - `service/kline/tests/processing_cursor_repo_test.py`
   - `service/kline/tests/projection_pool_catalog_repo_test.py`
   - `service/kline/tests/query_stack_api_test.py`
   - `service/kline/tests/query_stack_projection_position_metrics_fee_to_mixin.py`
   - `service/kline/tests/query_stack_projection_position_metrics_fetcher_mixin.py`
   - `service/kline/tests/query_stack_read_model_test.py`
   - `service/kline/tests/query_stack_read_model_test_support.py`
   - `service/kline/tests/query_stack_snapshot_fast_path_baseline_mixin.py`
   - `service/kline/tests/query_stack_snapshot_fast_path_fee_to_mixin.py`
   - `service/kline/tests/query_stack_snapshot_fast_path_materialized_mixin.py`
   - `service/kline/tests/query_stack_snapshot_fast_path_support_mixin.py`
   - `service/kline/tests/query_stack_snapshot_fast_path_test.py`
   - `service/kline/tests/query_stack_snapshot_shadow_mixin.py`
   - `service/kline/tests/query_stack_test_support.py`
   - `service/kline/tests/raw_repo_test.py`
   - `service/kline/tests/realtime_payload_builder_test.py`
   - `service/kline/tests/request_trace_test.py`
   - `service/kline/tests/rust_decoder_runner_test.py`
   - `service/kline/tests/rust_fixture_loader.py`
   - `service/kline/tests/settled_liquidity_change_repo_test.py`
   - `service/kline/tests/settled_liquidity_projection_repo_test.py`
   - `service/kline/tests/settled_market_deriver_test.py`
   - `service/kline/tests/settled_output_batch_test.py`
   - `service/kline/tests/settled_pool_history_projection_repo_test.py`
   - `service/kline/tests/settled_product_transaction_adapter_test.py`
   - `service/kline/tests/settled_trade_projection_repo_test.py`
   - `service/kline/tests/settled_trade_repo_test.py`
   - `service/kline/tests/subscription_test.py`
   - `service/kline/tests/swap_test.py`
   - `service/kline/tests/time_codec_test.py`
   - `service/kline/tests/trader_test.py`
   - `service/kline/tests/transaction_family_codec_test.py`
   - `service/kline/tests/transaction_watermarks_query_repo_test.py`
   - `service/kline/tests/virtual_positions_read_model_test.py`
   - `service/kline/tests/websocket_test.py`
3. Frontend test files:
   - `webui-v2/src/bridge/db/klineCacheCompatibility.test.ts`
   - `webui-v2/src/bridge/db/klinePersistence.test.ts`
   - `webui-v2/src/components/kline/chart/chartDataUpdate.test.ts`
   - `webui-v2/src/components/kline/chart/indicatorRenderScheduler.test.ts`
   - `webui-v2/src/components/kline/chart/visibleRangeLoad.test.ts`
   - `webui-v2/src/components/kline/loadQueue.test.ts`
   - `webui-v2/src/components/kline/priceChartMemorySnapshots.test.ts`
   - `webui-v2/src/components/kline/priceChartPointState.test.ts`
   - `webui-v2/src/components/kline/priceChartStartup.test.ts`
   - `webui-v2/src/components/kline/startupBaseline.test.ts`
   - `webui-v2/src/components/kline/startupInstrumentation.test.ts`
   - `webui-v2/src/components/meme/createMemeMetadata.test.ts`
   - `webui-v2/src/components/pools/poolFlow.test.ts`
   - `webui-v2/src/components/trending/trendingData.test.ts`
   - `webui-v2/src/controller/clientMigrations.test.ts`
   - `webui-v2/src/stores/ams/pagination.test.ts`
   - `webui-v2/src/stores/kline/liveUpdate.test.ts`
   - `webui-v2/src/stores/kline/poolStats.test.ts`
   - `webui-v2/src/stores/swap/poolIdentity.test.ts`
   - `webui-v2/src/utils/protocol.test.ts`
   - `webui-v2/src/worker/kline/listenerRegistry.test.ts`
   - `webui-v2/src/worker/kline/pointMerge.test.ts`
   - `webui-v2/src/worker/kline/runnerRequestTrace.test.ts`

### Gate 1B Acceptance Criteria

Gate 1B is accepted only if:

1. Every in-scope Gate 2 audit row maps to exactly one Gate 1A layer and one Gate 1B path entry.
2. Gate 2 does not audit files outside this Gate 1B list.
3. Gate 2 findings use concrete file paths from this list and do not cite a directory as the audited unit.
4. Generated frontend GraphQL files under `webui-v2/src/__generated__/graphql/` are build outputs and are out of scope.
5. Python cache directories, Rust build outputs, frontend build outputs, package-manager caches, and editor metadata are out of scope.
6. Quasar framework files are out of scope and must not be audited or modified by Gate 2:
   - `webui-v2/quasar.config.ts`
   - `webui-v2/src/boot/axios.ts`
   - `webui-v2/src/boot/i18n.ts`
   - `webui-v2/src/boot/notify-defaults.ts`
   - `webui-v2/src/boot/pinia.ts`

## Gate 1C Fixed Protocol Paths

Gate 2 must audit these fixed protocol paths. Each path must be audited as a complete protocol workflow across operation, message, handler, runtime capability, state, product entry, projection, and tests.

### Gate 1C Path 1: CreateMeme

`CreateMeme` is a fixed multi-step protocol path. Gate 2 must not audit it as a single handler.

1. Public operation entry:
   - `ProxyOperation::CreateMeme`
   - `proxy/src/contract_inner/handlers/operation/create_meme.rs`
2. Operation-side effects:
   - sets `meme_instantiation_argument.proxy_application_id`
   - copies `virtual_initial_liquidity`
   - copies `initial_liquidity`
   - sets `meme_parameters.creator` from authenticated account
   - funds proxy creator chain `AccountOwner::CHAIN` with `open_chain_fee_budget()` through `transfer_combined`
   - when `initial_liquidity` exists, funds authenticated signer on proxy creator chain with `open_chain_fee_budget()` through `transfer_combined`
   - when `virtual_initial_liquidity == false` and `initial_liquidity` exists, funds authenticated signer on proxy creator chain with initial native liquidity through `transfer_combined`
   - sends `ProxyMessage::CreateMeme` to `application_creator_chain_id`
3. Creator-chain message:
   - `ProxyMessage::CreateMeme`
   - `proxy/src/contract_inner/handlers/message/create_meme.rs`
4. Creator-chain side effects:
   - sets `instantiation_argument.swap_application_id`
   - opens meme chain with runtime `open_chain`
   - applies meme-chain permissions including `execute_operations`, `close_chain`, `change_application_permissions`, `call_service_as_oracle`, and `make_http_requests`
   - when `initial_liquidity` exists, initializes meme-chain funding amount to `open_chain_fee_budget()`
   - when `initial_liquidity` exists and `virtual_initial_liquidity == false`, adds `liquidity.native_amount` to meme-chain funding amount
   - reads authenticated signer before the zero-amount return inside `fund_meme_chain_initial_liquidity(...)`
   - when meme-chain funding amount is positive, requires authenticated signer proxy-chain owner balance to cover that amount
   - when meme-chain funding amount is positive, transfers from authenticated signer on proxy creator chain to authenticated signer on newly opened meme chain
   - sends `ProxyMessage::CreateMemeExt` to the newly opened meme chain
   - records created chain in proxy state through `state.create_chain(chain_id, system_time)`
5. Meme-chain message:
   - `ProxyMessage::CreateMemeExt`
   - `proxy/src/contract_inner/handlers/message/create_meme_ext.rs`
6. Meme-chain side effects:
   - creates meme application through runtime `create_application`
   - changes application permissions through runtime `change_application_permissions`
   - sends `ProxyMessage::MemeCreated` back to proxy creator chain
7. Completion message:
   - `ProxyMessage::MemeCreated`
   - `proxy/src/contract_inner/handlers/message/meme_created.rs`
8. Completion side effects:
   - writes meme chain token truth through `state.create_chain_token(chain_id, token)`
9. Required audit output:
   - exact source of creator account
   - exact source of signer account
   - exact creator-chain handler branch that reads authenticated signer even when meme-chain funding amount is zero
   - exact source of meme chain id
   - exact source of meme application id
   - exact fee-budget funding movements
   - exact initial-liquidity funding movements
   - exact state write that marks the created chain
   - whether `MemeCreated` creates a unique terminal truth for created meme token
   - whether failed, bounced, duplicate, stale, or partially completed create-meme workflows have terminal truth
   - whether product truth reads created meme existence from proxy state, projection, live query, or multiple sources

### Gate 1C Path 2: Meme Mining / Redeem

`Meme Mining / Redeem` is a fixed protocol path. Gate 2 must audit meme token mining reward accrual and meme-chain balance exit.

1. Public operation entries:
   - `MemeOperation::Mine`
   - `MemeOperation::Redeem`
2. Mine operation handler:
   - `meme/src/contract_inner/handlers/operation/mine.rs`
3. Mine operation side effects:
   - requires runtime `enable_mining()`
   - reads current block height through runtime `block_height()`
   - reads mined height through state `mining_height()`
   - requires current block height to be greater than or equal to mined height
   - reads current chain id through runtime `chain_id()`
   - reads signer through runtime `authenticated_signer()`
   - reads previous nonce through state `previous_nonce()`
   - builds `MiningBase` from height, nonce, chain id, signer, and previous nonce
   - hashes `MiningBase`
   - reads mining target through state `mining_target()`
   - requires mining hash to be less than or equal to mining target
   - updates `mining_height` to current block height plus one
   - updates `previous_nonce` to operation nonce
   - writes mining info through `state.update_mining_info(...)`
   - reads reward owner through runtime `authenticated_account()`
   - reads reward timestamp through runtime `system_time()`
   - mints mining reward through `state.mining_reward(owner, now)`
4. Redeem operation handler:
   - `meme/src/contract_inner/handlers/operation/redeem.rs`
5. Redeem operation side effects:
   - reads owner through runtime `authenticated_account()`
   - sends `MemeMessage::Redeem` to `application_creator_chain_id`
   - sets message `owner` to authenticated account
   - sets message `amount` to operation amount
6. Redeem message entry:
   - `MemeMessage::Redeem`
7. Redeem message handler:
   - `meme/src/contract_inner/handlers/message/redeem.rs`
8. Redeem message side effects:
   - reads current chain id through runtime `chain_id()`
   - builds `from` as current chain id plus `owner.owner`
   - when message amount is present, uses message amount
   - when message amount is absent, reads full source balance through `state.balance_of(from)`
   - transfers meme-chain balance through `state.transfer(from, owner, amount)`
9. Current state methods:
   - `meme/src/state/state_impl.rs::mining_reward`
   - `meme/src/state/state_impl.rs::mint`
   - `meme/src/state/state_impl.rs::balance_of`
   - `meme/src/state/state_impl.rs::transfer`
10. Required audit output:
   - how mining reward amount is determined
   - which account receives mining reward
   - which state fields determine mining height, nonce, target, reward amount, and mining start state
   - where mined token balance is stored
   - how `Redeem` moves meme-chain balance to owner account
   - exact source account constructed by redeem message handling
   - exact destination account supplied by redeem operation handling
   - exact amount selection behavior when redeem amount is present
   - exact amount selection behavior when redeem amount is absent
   - which source-chain, authenticated-caller, owner, amount, and state checks currently exist
   - whether `Redeem` is a local meme balance movement or a cross-chain asynchronous funds-exit path
   - whether target design keeps `Redeem` separate from pool `Claim` or routes redeemable meme balances through unified `Claim`

### Gate 1C Path 3: Meme InitializeLiquidity

`Meme InitializeLiquidity` is a fixed protocol path across `meme`, `swap`, and `pool`.

1. Meme instantiation entry:
   - `meme/src/contract_impl.rs::_instantiate`
   - `meme/src/contract_inner/instantiation_handler.rs`
2. Meme instantiation side effects:
   - requires authenticated signer to equal runtime `creator_signer()`
   - reads creator through runtime `creator()`
   - reads meme application account through runtime `application_account()`
   - copies runtime `virtual_initial_liquidity()` into instantiation argument
   - copies runtime `initial_liquidity()` into instantiation argument
   - reads mining enablement through runtime `enable_mining()`
   - reads mining supply through runtime `mining_supply()`
   - reads current timestamp through runtime `system_time()`
   - initializes meme state through `state.instantiate(...)`
   - mints `state.initial_owner_balance()` to creator through `state.mint(...)`
   - when runtime initial liquidity exists, calls `state.initialize_liquidity(liquidity, swap_creator_chain_id, enable_mining, mining_supply)`
   - registers application through AMS when AMS application id exists
   - registers logo through blob gateway when blob gateway application id exists
   - creates liquidity-pool funding outcome through instantiation handler `create_liquidity_pool()`
3. Meme state instantiation side effects:
   - `meme/src/state/state_impl.rs::instantiate`
   - writes `swap_application_id`
   - writes initial supply to meme application account balance
   - writes holder account
   - writes owner account
   - writes total supply into meme state
   - writes blob gateway application id
   - writes AMS application id
   - writes proxy application id
   - initializes mining info when mining is enabled
4. Meme state initialize-liquidity side effects:
   - `meme/src/state/state_impl.rs::initialize_liquidity`
   - reads holder balance
   - derives effective mining supply from runtime mining supply or holder balance when mining is enabled
   - sets mining supply to zero when mining is disabled
   - requires holder balance to cover requested fungible liquidity
   - requires holder balance to cover mining supply
   - caps fungible liquidity to `holder_balance - mining_supply` when mining is enabled and requested fungible liquidity exceeds that cap
   - returns without writing initial liquidity when effective fungible liquidity is zero
   - writes adjusted initial liquidity into meme state
   - builds swap spender account from swap creator chain id and swap application id
   - approves swap spender for adjusted fungible liquidity through `state.approve(...)`
5. Meme liquidity-pool funding side effects:
   - `meme/src/contract_inner/instantiation_handler.rs::create_liquidity_pool`
   - returns without message when swap application id is absent
   - returns without message when runtime initial liquidity is absent
   - returns without message when runtime fungible amount is zero
   - returns without message when runtime native amount is zero
   - funds swap creator chain open-chain fee budget through runtime `transfer_combined`
   - when runtime virtual initial liquidity is false, funds swap application native liquidity through runtime `transfer_combined`
   - sends `MemeMessage::LiquidityFunded` to `application_creator_chain_id`
6. Meme funding callback entry:
   - `MemeMessage::LiquidityFunded`
   - `meme/src/contract_inner/handlers/message/liquidity_funded.rs`
7. Meme callback side effects:
   - reads `virtual_initial_liquidity` from runtime parameters
   - reads `_initial_liquidity()` from meme state
   - reads `swap_application_id()` from meme state
   - builds `SwapOperation::InitializeLiquidity`
   - sets `creator` from runtime `creator()`
   - sets `token_0_creator_chain_id` from runtime `chain_id()`
   - sets `token_0` from runtime `application_id().forget_abi()`
   - sets `amount_0` from `liquidity.fungible_amount`
   - sets `amount_1` from `liquidity.native_amount`
   - calls swap application through runtime `call_application`
8. Swap operation entry:
   - `SwapOperation::InitializeLiquidity`
   - `swap/src/contract_inner/handlers/operation/initialize_liquidity.rs`
9. Swap operation side effects:
   - requires `authenticated_caller_id() == token_0`
   - requires current `chain_id() == token_0_creator_chain_id`
   - formalizes virtual liquidity only when caller application is `token_0`, token pair is native, and current chain is token creator chain
   - sends `SwapMessage::InitializeLiquidity` to `application_creator_chain_id`
10. Swap creator-chain message:
   - `SwapMessage::InitializeLiquidity`
   - `swap/src/contract_inner/handlers/message/initialize_liquidity.rs`
11. Swap creator-chain side effects:
   - delegates to `swap/src/contract_inner/handlers/create_pool.rs::CreatePoolHandler`
   - passes `token_1_creator_chain_id = None`
   - passes `token_1 = None`
   - passes `user_pool = false`
12. Pool-chain opening:
   - `swap/src/contract_inner/handlers/create_pool.rs`
13. Pool-chain opening side effects:
   - opens pool chain through runtime `open_chain`
   - applies pool-chain permissions including router application and meme token application
   - records pool chain through `state.create_pool_chain(destination)`
   - sends `SwapMessage::CreatePool` to the newly opened pool chain
14. Pool application creation:
   - `SwapMessage::CreatePool`
   - `swap/src/contract_inner/handlers/message/create_pool.rs`
15. Pool application creation side effects:
   - creates pool application through runtime `create_application`
   - passes `PoolParameters`
   - passes `PoolInstantiationArgument`
   - because `user_pool == false`, instantiation receives non-zero `amount_0` and `amount_1`
   - sends `SwapMessage::PoolCreated` back to swap creator chain
16. Pool instantiation side effects:
   - `pool/src/contract_impl.rs::_instantiate`
   - calls pool state `instantiate(...)`
   - if both instantiation amounts are positive, builds initial liquidity transaction
   - sends `PoolMessage::NewTransaction` to current pool chain
17. Swap pool-created completion:
   - `SwapMessage::PoolCreated`
   - `swap/src/contract_inner/handlers/message/pool_created.rs`
18. Swap pool-created completion side effects for initial liquidity:
   - requires `state.is_pool_chain(pool_application.chain_id)`
   - requires positive `amount_0`
   - requires positive `amount_1`
   - checks `state.get_pool_exchangable(token_0, token_1)` before creating pool truth
   - calls `initial_pool_created(...)` before writing swap pool truth
   - inside `initial_pool_created(...)`, when `virtual_initial_liquidity == false`, transfers native `amount_1` from router application account to pool application account through runtime `transfer`
   - inside `initial_pool_created(...)`, calls meme application through runtime `call_application`
   - inside `initial_pool_created(...)`, call payload is `MemeOperation::InitializeLiquidity`
   - inside `initial_pool_created(...)`, call sets `to` to pool application account
   - inside `initial_pool_created(...)`, call sets `amount` to `amount_0`
   - after `initial_pool_created(...)` returns, creates swap pool truth through `state.create_pool(...)`
19. Meme initialize-liquidity operation:
   - `MemeOperation::InitializeLiquidity`
   - `meme/src/contract_inner/handlers/operation/initialize_liquidity.rs`
20. Meme initialize-liquidity operation side effects:
   - reads authenticated caller application through `authenticated_caller_id()`
   - builds caller account from current chain id and authenticated caller application id
   - sends `MemeMessage::InitializeLiquidity` to `application_creator_chain_id`
21. Meme initialize-liquidity creator-chain message:
   - `MemeMessage::InitializeLiquidity`
   - `meme/src/contract_inner/handlers/message/initialize_liquidity.rs`
22. Meme initialize-liquidity creator-chain side effects:
   - requires caller chain id equals runtime `swap_creator_chain_id()`
   - requires caller owner equals state `swap_application_id()`
   - reads meme application creation account through runtime `application_creation_account()`
   - transfers meme balance through state `transfer_from(caller, from, to, amount)`
   - changes meme chain ownership through `OpenMultiLeaderRoundsHandler`
23. Transaction propagation:
   - `PoolMessage::NewTransaction`
   - `pool/src/contract_inner/handlers/message/new_transaction.rs`
24. Transaction propagation side effects:
   - reads price pair from pool state
   - reads reserves from pool state
   - calls router application through runtime `call_application`
   - call payload is `SwapOperation::UpdatePool`
25. Swap update-pool operation:
   - `SwapOperation::UpdatePool`
   - `swap/src/contract_inner/handlers/operation/update_pool.rs`
26. Swap update-pool operation side effects:
   - sends `SwapMessage::UpdatePool` to `application_creator_chain_id`
27. Swap update-pool message:
   - `SwapMessage::UpdatePool`
   - `swap/src/contract_inner/handlers/message/update_pool.rs`
28. Swap update-pool side effects:
   - writes router pool truth through `state.update_pool(token_0, token_1, transaction, token_0_price, token_1_price, reserve_0, reserve_1)`
29. Required audit output:
   - exact source of initial liquidity amounts
   - exact adjusted initial liquidity after mining-supply cap
   - exact initial liquidity allowance owner, spender, and amount
   - exact source of virtual-liquidity truth
   - exact caller authentication checks at meme and swap boundaries
   - exact chain identity checks at meme and swap boundaries
   - exact runtime call boundary from meme to swap
   - exact runtime open-chain boundary for pool creation
   - exact pool application creation arguments
   - exact state write that marks pool chain creation
   - exact native initial-liquidity transfer from router application account to pool application account
   - exact meme initial-liquidity transfer from meme application creation account to pool application account
   - exact meme chain ownership change after initialization
   - exact transaction emitted for initial liquidity
   - exact router pool truth update after transaction propagation
   - exact ordering relationship between `PoolCreated -> initial_pool_created(...)` and `PoolCreated -> state.create_pool(...)`
   - exact ordering relationship between `PoolCreated -> state.create_pool(...)` and `NewTransaction -> SwapOperation::UpdatePool`
   - whether `UpdatePoolHandler` can execute before router pool truth exists
   - whether this path has terminal truth for early, duplicate, or stale `UpdatePool`
   - whether failed, bounced, duplicate, stale, or partially completed initialize-liquidity workflows have terminal truth
   - whether product truth reads initialized liquidity from pool state, swap state, projection, live query, or multiple sources

### Gate 1C Path 4: User CreatePool With Initial Liquidity

`User CreatePool With Initial Liquidity` is a fixed protocol path. Gate 2 must audit it separately from `Meme InitializeLiquidity`.

1. User operation entry:
   - `SwapOperation::CreatePool`
   - `swap/src/contract_inner/handlers/operation/create_pool.rs`
2. User operation side effects:
   - requires `token_0 != token_1`
   - reads authenticated signer through `authenticated_signer()`
   - funds swap creator chain open-chain fee budget through runtime `transfer`
   - resolves `token_0_creator_chain_id` through runtime `token_creator_chain_id(token_0)`
   - resolves `token_1_creator_chain_id` through runtime `token_creator_chain_id(token_1)` when `token_1` exists
   - sends `SwapMessage::CreateUserPool` to `application_creator_chain_id`
3. Swap creator-chain message:
   - `SwapMessage::CreateUserPool`
   - `swap/src/contract_inner/handlers/message/create_user_pool.rs`
4. Swap creator-chain side effects:
   - requires `token_0 != token_1`
   - checks `state.get_pool_exchangable(token_0, token_1)` before opening a pool chain
   - sets pool creator from `message_signer_account()`
   - resolves token creator chain ids through runtime `token_creator_chain_id`
   - delegates to `swap/src/contract_inner/handlers/create_pool.rs::CreatePoolHandler`
   - passes `virtual_initial_liquidity = false`
   - passes `user_pool = true`
5. Pool-chain opening:
   - `swap/src/contract_inner/handlers/create_pool.rs`
6. Pool-chain opening side effects:
   - opens pool chain through runtime `open_chain`
   - applies pool-chain permissions including router application, token_0 application, and token_1 application when token_1 exists
   - records pool chain through `state.create_pool_chain(destination)`
   - sends `SwapMessage::CreatePool` to the newly opened pool chain
7. Pool application creation:
   - `SwapMessage::CreatePool`
   - `swap/src/contract_inner/handlers/message/create_pool.rs`
8. Pool application creation side effects:
   - creates pool application through runtime `create_application`
   - passes `PoolParameters`
   - passes `PoolInstantiationArgument`
   - because `user_pool == true`, instantiation receives zero `amount_0` and zero `amount_1`
   - sends `SwapMessage::PoolCreated` back to swap creator chain
9. Pool-created completion:
   - `SwapMessage::PoolCreated`
   - `swap/src/contract_inner/handlers/message/pool_created.rs`
10. Pool-created completion side effects:
   - requires `state.is_pool_chain(pool_application.chain_id)`
   - requires positive `amount_0` and positive `amount_1`
   - checks `state.get_pool_exchangable(token_0, token_1)` before creating pool truth
   - creates swap pool truth through `state.create_pool(...)`
   - because `user_pool == true`, sends `SwapMessage::UserPoolCreated` to `creator.chain_id`
11. User-pool completion:
   - `SwapMessage::UserPoolCreated`
   - `swap/src/contract_inner/handlers/message/user_pool_created.rs`
12. Required audit output:
   - exact source of user signer
   - exact source of pool creator
   - exact source of both token creator chain ids
   - exact open-chain fee-budget movement
   - exact pool-chain permission set
   - exact pool application creation arguments
   - exact state writes for pool chain and pool truth
   - exact reason pool instantiation starts with zero liquidity
   - exact follow-up path that converts `UserPoolCreated` into initial liquidity funding
   - whether fee-budget refund exists when pool already exists
   - whether failed, bounced, duplicate, stale, or partially completed create-pool workflows have terminal truth
   - whether product truth reads user-created pool existence from swap state, projection, live query, or multiple sources

### Gate 1C Path 5: AddLiquidity Funding

`AddLiquidity Funding` is a fixed protocol path. It covers direct existing-pool add liquidity and first add liquidity triggered by `UserPoolCreated`.

1. User-pool-created trigger:
   - `SwapMessage::UserPoolCreated`
   - `swap/src/contract_inner/handlers/message/user_pool_created.rs`
2. User-pool-created side effects:
   - calls `state.mark_user_pool_created(pool_application)`
   - returns without side effects when `mark_user_pool_created` reports already processed
   - converts `pool_application.owner` into `ApplicationId`
   - calls pool application through runtime `call_application`
   - call payload is `PoolOperation::AddLiquidity`
   - sets `amount_0_in` from `SwapMessage::UserPoolCreated.amount_0`
   - sets `amount_1_in` from `SwapMessage::UserPoolCreated.amount_1`
   - sets `to` from `SwapMessage::UserPoolCreated.to`
   - sets both min amounts and block timestamp to `None`
3. Direct user operation entry:
   - `PoolOperation::AddLiquidity`
   - `pool/src/contract_inner/handlers/operation/add_liquidity.rs`
4. Add-liquidity operation side effects:
   - requires positive `amount_0_in`
   - requires positive `amount_1_in`
   - sets origin from runtime `authenticated_account()`
   - reads token_0 from runtime `token_0()`
   - reads token_1 from runtime `token_1()`
   - creates first `FundRequest` for token_0 with `FundStatus::InFlight`
   - creates second `FundRequest` for token_1 or native token with `FundStatus::Created`
   - links first request to second request with `next_request`
   - links second request to first request with `prev_request`
   - sends first funding request through `pool/src/contract_inner/handlers/request_meme_fund.rs`
5. Meme-token funding request:
   - `PoolMessage::RequestFund`
   - `pool/src/contract_inner/handlers/request_meme_fund.rs`
6. Meme-token funding request side effects:
   - resolves token creator chain id through runtime `token_creator_chain_id(token)`
   - sends `PoolMessage::RequestFund` to token creator chain
7. Token creator-chain funding response:
   - `PoolMessage::RequestFund`
   - `pool/src/contract_inner/handlers/message/request_fund.rs`
8. Token creator-chain funding response side effects:
   - calls meme application through runtime `call_application`
   - call payload is `MemeOperation::TransferToCaller`
   - sends `PoolMessage::FundSuccess` back to message origin chain when response is `MemeResponse::Ok`
   - sends `PoolMessage::FundFail` back to message origin chain when response is `MemeResponse::Fail`
9. Fund success:
   - `PoolMessage::FundSuccess`
   - `pool/src/contract_inner/handlers/message/fund_success.rs`
10. Fund success side effects:
   - loads `FundRequest` by `transfer_id`
   - changes request status to `FundStatus::Success`
   - writes updated request through `state.update_fund_request`
   - when the completed request has `next_request`, loads the next request
   - if next request has a meme token, sends the next request through `RequestMemeFundHandler`
   - if next request is native token, funds pool application creation chain through `FundPoolApplicationCreationChainHandler`
   - after both asset requests are available, transfers meme assets to pool application creation account through `TransferMemeFromApplicationHandler`
   - sends `PoolMessage::AddLiquidity` to `application_creator_chain_id`
11. Native funding helper:
   - `pool/src/contract_inner/handlers/fund_pool_application_creation_chain.rs`
12. Native funding helper side effects:
   - reads pool application creation account through runtime `application_creation_account()`
   - transfers native amount through runtime `transfer_combined(None, application, amount)`
13. Pool creator-chain add-liquidity message:
   - `PoolMessage::AddLiquidity`
   - `pool/src/contract_inner/handlers/message/add_liquidity.rs`
14. Pool creator-chain add-liquidity side effects:
   - calculates accepted token amounts through `state.try_calculate_swap_amount_pair`
   - sets LP recipient to message `to` when present
   - sets LP recipient to `origin` when message `to` is absent
   - mints LP through `state.add_liquidity`
   - refunds excess token_0 through meme `TransferFromApplication`
   - refunds excess meme token_1 through meme `TransferFromApplication`
   - refunds excess native token_1 through runtime `transfer`
   - builds transaction through `state.build_transaction`
   - sends `PoolMessage::NewTransaction` to current pool chain
15. Transaction propagation:
   - `PoolMessage::NewTransaction`
   - `pool/src/contract_inner/handlers/message/new_transaction.rs`
16. Transaction propagation side effects:
   - reads price pair from pool state
   - reads reserves from pool state
   - calls router application through runtime `call_application`
   - call payload is `SwapOperation::UpdatePool`
17. Swap update-pool operation:
   - `SwapOperation::UpdatePool`
   - `swap/src/contract_inner/handlers/operation/update_pool.rs`
18. Swap update-pool operation side effects:
   - sends `SwapMessage::UpdatePool` to `application_creator_chain_id`
19. Swap update-pool message:
   - `SwapMessage::UpdatePool`
   - `swap/src/contract_inner/handlers/message/update_pool.rs`
20. Swap update-pool side effects:
   - writes router pool truth through `state.update_pool(token_0, token_1, transaction, token_0_price, token_1_price, reserve_0, reserve_1)`
21. Required audit output:
   - exact source of liquidity origin
   - exact source of LP recipient
   - exact token_0 and token_1 identity source
   - exact `FundRequest` state machine
   - exact transfer id linkage between both asset requests
   - exact meme funding request route
   - exact native funding route
   - exact success and fail handling for each asset
   - exact point where assets are moved to pool application creation account
   - exact accepted amount calculation and refund behavior
   - exact LP mint state mutation
   - exact transaction emitted for add liquidity
   - exact router update call after transaction propagation
   - exact router pool truth update after transaction propagation
   - exact status transition for native second fund request
   - whether native second fund request remains `FundStatus::Created` after native funding
   - whether add-liquidity terminal truth depends on fund request status or `PoolMessage::AddLiquidity` execution
   - whether failed, bounced, duplicate, stale, or partially completed add-liquidity workflows have terminal truth
   - whether product truth reads add-liquidity completion from pool state, transaction projection, live query, or multiple sources

### Gate 1C Path 6: Swap Funding And Settlement

`Swap Funding And Settlement` is a fixed protocol path. It shares meme funding request mechanics with `AddLiquidity Funding`, but settlement, refund, and output dispatch are audited independently.

1. User operation entry:
   - `PoolOperation::Swap`
   - `pool/src/contract_inner/handlers/operation/swap.rs`
2. Swap operation side effects:
   - requires exactly one of `amount_0_in` and `amount_1_in` to exist
   - requires provided input amount to be positive
   - sets origin from runtime `authenticated_account()`
   - reads token_0 from runtime `token_0()`
   - reads token_1 from runtime `token_1()`
   - when input is token_0, creates one `FundRequest` with token_0, `FundType::Swap`, and `FundStatus::InFlight`
   - when input is meme token_1, creates one `FundRequest` with token_1, `FundType::Swap`, and `FundStatus::InFlight`
   - when input is native token_1, funds pool application creation chain through `FundPoolApplicationCreationChainHandler`
   - when input is native token_1, sends `PoolMessage::Swap` directly to `application_creator_chain_id`
   - when input is meme token, sends funding request through `RequestMemeFundHandler`
3. Meme-token funding request:
   - `PoolMessage::RequestFund`
   - `pool/src/contract_inner/handlers/request_meme_fund.rs`
4. Token creator-chain funding response:
   - `PoolMessage::RequestFund`
   - `pool/src/contract_inner/handlers/message/request_fund.rs`
5. Meme-token funding response side effects:
   - calls meme application through runtime `call_application`
   - call payload is `MemeOperation::TransferToCaller`
   - sends `PoolMessage::FundSuccess` back to message origin chain when response is `MemeResponse::Ok`
   - sends `PoolMessage::FundFail` back to message origin chain when response is `MemeResponse::Fail`
6. Fund success:
   - `PoolMessage::FundSuccess`
   - `pool/src/contract_inner/handlers/message/fund_success.rs`
7. Fund success side effects for swap:
   - loads `FundRequest` by `transfer_id`
   - changes request status to `FundStatus::Success`
   - writes updated request through `state.update_fund_request`
   - transfers meme input to pool application creation account through `TransferMemeFromApplicationHandler`
   - sends `PoolMessage::Swap` to `application_creator_chain_id`
8. Fund fail:
   - `PoolMessage::FundFail`
   - `pool/src/contract_inner/handlers/message/fund_fail.rs`
9. Fund fail side effects:
   - loads `FundRequest` by `transfer_id`
   - changes request status to `FundStatus::Fail`
   - records fail error on `FundRequest.error`
   - writes updated request through `state.update_fund_request`
10. Pool creator-chain swap message:
   - `PoolMessage::Swap`
   - `pool/src/contract_inner/handlers/message/swap.rs`
11. Pool creator-chain swap side effects:
   - calculates output amount through `state.calculate_swap_amount_0` or `state.calculate_swap_amount_1`
   - validates minimum output amount
   - refunds input through `RefundHandler` when minimum output is not met
   - rejects zero output and refunds input through `RefundHandler`
   - validates swap invariant through `state.pool().validate_swap_invariant`
   - refunds input through `RefundHandler` when invariant validation fails
   - checks native token_1 application balance before native output dispatch
   - refunds input through `RefundHandler` when native token_1 application balance is insufficient
   - returns `Err(HandlerError::InvalidAmount)` after refund when minimum output is not met
   - returns `Err(HandlerError::InvalidAmount)` after refund when output amount is zero
   - returns `Err(HandlerError::InvalidAmount)` or `Err(HandlerError::InsufficientFunds)` after refund when invariant validation fails
   - returns `Err(HandlerError::InsufficientFunds)` after refund when native token_1 application balance is insufficient
   - catches `do_swap(...)` errors in message `handle(...)`, logs the failure, and returns `Ok(None)`
   - updates reserves through `state.liquid`
   - builds transaction through `state.build_transaction`
   - sends `PoolMessage::NewTransaction` to current pool chain
   - dispatches meme token output through `TransferMemeFromApplicationHandler`
   - dispatches native token_1 output through runtime `transfer`
12. Transaction propagation:
   - `PoolMessage::NewTransaction`
   - `pool/src/contract_inner/handlers/message/new_transaction.rs`
13. Transaction propagation side effects:
   - reads price pair from pool state
   - reads reserves from pool state
   - calls router application through runtime `call_application`
   - call payload is `SwapOperation::UpdatePool`
14. Swap update-pool operation:
   - `SwapOperation::UpdatePool`
   - `swap/src/contract_inner/handlers/operation/update_pool.rs`
15. Swap update-pool operation side effects:
   - sends `SwapMessage::UpdatePool` to `application_creator_chain_id`
16. Swap update-pool message:
   - `SwapMessage::UpdatePool`
   - `swap/src/contract_inner/handlers/message/update_pool.rs`
17. Swap update-pool side effects:
   - writes router pool truth through `state.update_pool(token_0, token_1, transaction, token_0_price, token_1_price, reserve_0, reserve_1)`
18. Required audit output:
   - exact source of swap origin
   - exact token input branch
   - exact native input funding route
   - exact meme input funding route
   - exact `FundRequest` state machine for swap
   - exact fail status and error persistence
   - exact point where meme input is moved to pool application creation account
   - exact output calculation formula entry
   - exact min-output validation behavior
   - exact invariant validation behavior
   - exact refund path for invalid swap settlement
   - exact post-refund error path inside `do_swap(...)`
   - exact message-handler behavior that converts `do_swap(...)` errors into `Ok(None)`
   - whether refund-plus-`Ok(None)` creates terminal workflow truth for failed settlement
   - exact reserve mutation
   - exact transaction emitted for swap
   - exact output dispatch route for meme output
   - exact output dispatch route for native output
   - exact router update call after transaction propagation
   - exact router pool truth update after transaction propagation
   - whether failed, bounced, duplicate, stale, or partially completed swap workflows have terminal truth
   - whether product truth reads swap completion from pool state, router state, transaction projection, live query, or multiple sources

### Gate 1C Path 7: RemoveLiquidity Funds Exit

`RemoveLiquidity Funds Exit` is a fixed protocol path. Gate 2 must audit it as a current direct payout path and not as unified `Claim`.

1. User operation entry:
   - `PoolOperation::RemoveLiquidity`
   - `pool/src/contract_inner/handlers/operation/remove_liquidity.rs`
2. Remove-liquidity operation side effects:
   - requires positive `liquidity`
   - sets origin from runtime `authenticated_account()`
   - sends `PoolMessage::RemoveLiquidity` to `application_creator_chain_id`
3. Pool creator-chain message:
   - `PoolMessage::RemoveLiquidity`
   - `pool/src/contract_inner/handlers/message/remove_liquidity.rs`
4. Pool creator-chain side effects:
   - sets timestamp from message `block_timestamp` when present
   - sets timestamp from runtime `system_time()` when message `block_timestamp` is absent
   - calls `state.remove_liquidity(origin, liquidity, amount_0_out_min, amount_1_out_min, timestamp)`
   - sets payout recipient to message `to` when present
   - sets payout recipient to `origin` when message `to` is absent
   - dispatches token_0 payout through `TransferMemeFromApplicationHandler`
   - dispatches meme token_1 payout through `TransferMemeFromApplicationHandler`
   - dispatches native token_1 payout through runtime `transfer`
   - builds transaction through `state.build_transaction`
   - sends `PoolMessage::NewTransaction` to current pool chain
5. State remove-liquidity side effects:
   - `pool/src/state/state_impl.rs::remove_liquidity`
   - computes protocol fee share through `pool.mint_fee(total_supply)`
   - mints protocol fee share to `pool.fee_to`
   - calculates output amounts through `try_calculate_liquidity_amount_pair`
   - burns LP shares from `origin`
   - reduces reserves through `pool.liquid`
   - updates `k_last`
   - returns `(amount_0, amount_1)`
6. Transaction propagation:
   - `PoolMessage::NewTransaction`
   - `pool/src/contract_inner/handlers/message/new_transaction.rs`
7. Transaction propagation side effects:
   - reads price pair from pool state
   - reads reserves from pool state
   - calls router application through runtime `call_application`
   - call payload is `SwapOperation::UpdatePool`
8. Swap update-pool operation:
   - `SwapOperation::UpdatePool`
   - `swap/src/contract_inner/handlers/operation/update_pool.rs`
9. Swap update-pool operation side effects:
   - sends `SwapMessage::UpdatePool` to `application_creator_chain_id`
10. Swap update-pool message:
   - `SwapMessage::UpdatePool`
   - `swap/src/contract_inner/handlers/message/update_pool.rs`
11. Swap update-pool side effects:
   - writes router pool truth through `state.update_pool(token_0, token_1, transaction, token_0_price, token_1_price, reserve_0, reserve_1)`
12. Required audit output:
   - exact source of remove-liquidity origin
   - exact source of payout recipient
   - exact LP burn account
   - exact protocol fee mint behavior
   - exact liquidity amount calculation entry
   - exact minimum output validation behavior
   - exact reserve mutation
   - exact token_0 payout route
   - exact meme token_1 payout route
   - exact native token_1 payout route
   - exact transaction emitted for remove liquidity
   - exact router update call after transaction propagation
   - exact router pool truth update after transaction propagation
   - whether failed, bounced, duplicate, stale, or partially completed remove-liquidity workflows have terminal truth
   - whether current direct payout must be replaced by claim-balance accrual in the target design
   - whether product truth reads remove-liquidity completion from pool state, router state, transaction projection, live query, or multiple sources

### Gate 1C Path 8: Unified Claim Target Gap

`Unified Claim Target Gap` is a fixed audit path. Gate 2 must not treat AMS `Claim` or Linera chain `claim` as FUND-005 funding claim.

1. Current non-funding claim objects:
   - `AmsOperation::Claim`
   - `AmsMessage::Claim`
   - `abi/src/ams.rs`
   - `service/kline/src/normalizer/application_event_family_resolver.py`
2. Current funding ABI gap:
   - no `PoolOperation::Claim` exists in `abi/src/swap/pool/mod.rs`
   - no `PoolMessage::Claim` exists in `abi/src/swap/pool/mod.rs`
   - no `SwapOperation::Claim` exists in `abi/src/swap/router.rs`
   - no `SwapMessage::Claim` exists in `abi/src/swap/router.rs`
   - no `MemeOperation::Claim` exists in `abi/src/meme.rs`
   - no `MemeMessage::Claim` exists in `abi/src/meme.rs`
3. Current funding state gap:
   - no claim-balance state is defined in `pool/src/interfaces/state.rs`
   - no claim-balance state is implemented in `pool/src/state/state_impl.rs`
   - no claiming/in-flight claim state is defined in `pool/src/interfaces/state.rs`
   - no claiming/in-flight claim state is implemented in `pool/src/state/state_impl.rs`
   - no claim-balance state is defined in `meme/src/interfaces/state.rs`
   - no claim-balance state is implemented in `meme/src/state/state_impl.rs`
4. Current direct funds-exit paths that must be audited against target claim model:
   - `RemoveLiquidity Funds Exit`
   - `Swap Funding And Settlement` output dispatch
   - `Swap Funding And Settlement` refund dispatch
   - `AddLiquidity Funding` refund dispatch
   - `Meme Mining / Redeem`
5. Required target-design audit output:
   - exact list of current direct payout sites
   - exact owner/account that would be credited in claim balance at each payout site
   - exact token/application/native asset identity that would be credited at each payout site
   - exact amount source that would be credited at each payout site
   - exact terminal state that should replace direct payout for each payout site
   - exact claiming state needed to prevent duplicate claim execution
   - exact runtime transfer capability needed by claim execution
   - exact close-chain behavior needed after claim execution
   - exact distinction between current `ApplicationPermissions.close_chain` permission configuration and missing runtime `close_chain(...)` execution capability
   - exact bounce/reject handling needed when claim transfer fails
   - exact projection events/read models needed for claimable and claiming balances
   - exact frontend `webui-v2` entry points needed for claimable and claiming balances
6. Required non-goals:
   - AMS claim remains outside FUND-005 funding claim
   - Linera chain claim remains outside FUND-005 funding claim
   - generated GraphQL files under `webui-v2/src/__generated__/graphql/` remain outside Gate 2 audit scope
   - obsolete `webui/` remains outside Gate 2 audit scope
7. Required audit output:
   - whether current implementation has zero unified funding claim support
   - whether Gate 2 must treat unified claim as target architecture rather than current implementation
   - whether each current direct funds-exit path has enough owner, token, amount, and terminal-state information to be converted into claim-balance accrual
   - whether product truth can expose claimable and claiming balances from projection without live-query double truth

### Gate 1C Path 9: Tracked Reject / Bounce Gap

`Tracked Reject / Bounce Gap` is a fixed audit path. Gate 2 must distinguish current runtime send behavior, current observational rejected facts, and target funding bounce/claim terminal truth.

1. Current runtime send boundary:
   - `runtime/src/interfaces/contract.rs::ContractRuntimeContext::send_message`
   - `runtime/src/contract.rs::ContractRuntimeAdapter::send_message`
2. Current runtime send behavior:
   - sends through `prepare_message(message)`
   - applies `.with_authentication()`
   - sends with `.send_to(destination)`
   - does not apply explicit tracking in the current adapter
   - does not expose a bounce receive API in `ContractRuntimeContext`
   - does not expose a close-chain API in `ContractRuntimeContext`
   - current `ApplicationPermissions.close_chain` entries are permission configuration facts, not runtime close-chain execution capability
3. Current handler outcome boundary:
   - `base/src/handler.rs::HandlerOutcome`
   - `base/src/handler.rs::HandlerMessage`
4. Current handler outcome behavior:
   - stores destination chain id
   - stores message payload
   - does not store tracking policy
   - does not store bounce policy
   - does not store terminal workflow id
   - does not store claim/compensation metadata
5. Current contract dispatch reality:
   - `swap/src/contract_impl.rs`
   - `pool/src/contract_impl.rs`
   - `meme/src/contract_impl.rs`
   - `proxy/src/contract_impl.rs`
6. Current contract dispatch behavior:
   - drains `HandlerOutcome.messages`
   - sends each message through runtime `send_message`
   - does not branch on tracked send result
   - does not dispatch bounced messages to funding handlers
   - does not persist bounced workflow terminal truth
7. Current rejected fact/projection reality:
   - `service/kline/src/storage/mysql/raw_repo.py`
   - `service/kline/src/normalizer/decode_result_normalizer.py`
   - `service/kline/src/normalizer/application_event_family_resolver.py`
   - `service/kline/src/normalizer/normalized_event_result.py`
8. Current rejected fact/projection behavior:
   - raw ingestion can mark execution status as `rejected`
   - normalizer preserves rejected status and reject reason
   - event-family resolver maps rejected pool, swap, meme, and proxy messages to rejected event families
   - rejected projection is observational
   - rejected projection does not currently drive contract compensation
   - rejected projection does not currently create claim balances
9. Current tests:
   - contract tests include rejected handler/input cases
   - integration tests consume messages with `MessageAction::Accept`
   - no fixed funding test proves tracked-message bounce recovery
   - no fixed funding test proves bounced direct payout becomes claimable balance
10. Required audit output:
   - exact runtime send calls that require tracking in target design
   - exact runtime close-chain execution capability required in target design
   - exact places that currently configure `ApplicationPermissions.close_chain`
   - exact message types whose failure must become terminal workflow truth
   - exact message types whose failure must credit claim balance
   - exact handlers that need bounced-message dispatch entries
   - exact state fields needed for bounce terminal truth
   - exact state fields needed for claim compensation after bounce
   - exact observability facts needed to expose pending, rejected, bounced, failed, claimable, and claiming states
   - exact tests needed to distinguish accepted, rejected, bounced, duplicate, and stale workflows
11. Required non-goals:
   - raw/projection `rejected` facts are not contract-level compensation
   - handler `assert!` rejection tests are not tracked-message bounce recovery
   - Linera test `MessageAction::Accept` coverage is not bounce coverage
   - obsolete `webui/` remains outside Gate 2 audit scope
   - generated GraphQL files under `webui-v2/src/__generated__/graphql/` remain outside Gate 2 audit scope

### Gate 1C Path 10: Projection And Product Truth

`Projection And Product Truth` is a fixed cross-cutting audit path. Gate 2 must audit product entry, routing, read models, and projection truth for funding workflows.

1. Frontend product entry boundaries:
   - `webui-v2/src/components/meme/CreateMemeView.vue`
   - `webui-v2/src/pages/AddLiquidityPage.vue`
   - `webui-v2/src/pages/RemoveLiquidityPage.vue`
   - `webui-v2/src/pages/SwapPage.vue`
   - `webui-v2/src/pages/PositionsPage.vue`
2. Frontend route and flow decision boundaries:
   - `webui-v2/src/components/pools/poolFlow.ts`
   - `webui-v2/src/stores/swap/poolIdentity.ts`
   - `webui-v2/src/router/routes.ts`
3. Frontend protocol submission boundaries:
   - `webui-v2/wasm/src/lib.rs`
   - `webui-v2/wasm/src/fake_proxy.rs`
   - `webui-v2/wasm/src/fake_swap.rs`
   - `webui-v2/wasm/src/fake_pool.rs`
   - `webui-v2/src/wallet/checko.ts`
   - `webui-v2/src/wallet/wallet.ts`
   - `webui-v2/src/wallet/provider.ts`
   - `webui-v2/src/wallet/linera_web_client.ts`
4. Frontend GraphQL declaration boundaries:
   - `webui-v2/src/graphql/swap.ts`
   - `webui-v2/src/graphql/swap_raw.ts`
   - `webui-v2/src/graphql/pool_raw.ts`
   - `webui-v2/src/graphql/meme_raw.ts`
   - `webui-v2/src/graphql/proxy.ts`
   - `webui-v2/src/graphql/proxy_raw.ts`
   - `webui-v2/src/graphql/service.ts`
   - `webui-v2/src/graphql/service_raw.ts`
5. Observability raw/normalization boundaries:
   - `service/kline/src/storage/mysql/raw_repo.py`
   - `service/kline/src/registry/pool_operation_decoder.py`
   - `service/kline/src/registry/pool_message_decoder.py`
   - `service/kline/src/registry/swap_operation_decoder.py`
   - `service/kline/src/registry/swap_message_decoder.py`
   - `service/kline/src/registry/meme_operation_decoder.py`
   - `service/kline/src/registry/meme_message_decoder.py`
   - `service/kline/src/registry/proxy_operation_decoder.py`
   - `service/kline/src/registry/proxy_message_decoder.py`
   - `service/kline/src/normalizer/decode_result_normalizer.py`
   - `service/kline/src/normalizer/application_event_family_resolver.py`
   - `service/kline/src/normalizer/normalized_event_result.py`
6. Observability projection/query boundaries:
   - `service/kline/src/market/pool_new_transaction_execution_fact_extractor.py`
   - `service/kline/src/market/settled_market_deriver.py`
   - `service/kline/src/market/position_metrics_snapshot_builder.py`
   - `service/kline/src/projection/projector.py`
   - `service/kline/src/query/handlers/positions.py`
   - `service/kline/src/query/handlers/position_metrics.py`
   - `service/kline/src/query/read_models/positions.py`
   - `service/kline/src/query/read_models/position_metrics.py`
   - `service/kline/src/query/serializers/positions.py`
7. Current product-truth decisions to audit:
   - how `CreateMeme` submit payload is built
   - how initial liquidity fields are serialized
   - how mining fields are serialized
   - how pool pair order is normalized
   - how frontend decides create-pool versus add-liquidity
   - how frontend resolves existing pool identity
   - how frontend submits swap, add liquidity, remove liquidity, and create pool
   - how frontend reads positions
   - how frontend reads pool reserves, LP, TVL, APR inputs, and transaction history
   - how frontend currently represents absent claimable and claiming balances
8. Current projection-truth decisions to audit:
   - which normalized event families exist for create meme, initialize liquidity, create pool, add liquidity, swap, remove liquidity, fund request, fund success, fund fail, new transaction, mine, redeem, and rejected messages
   - which event families are missing for claimable balances
   - which event families are missing for claiming balances
   - which event families are missing for bounced funding messages
   - which projection tables/read models expose pending workflows
   - which projection tables/read models expose failed workflows
   - which projection tables/read models expose stalled workflows
   - which projection tables/read models expose direct payout completion
   - which projection tables/read models would expose claimable and claiming balances in target design
9. Required audit output:
   - exact frontend entry point for each Gate 1C protocol path
   - exact wallet/provider capability used by each entry point
   - exact operation serialization path for each entry point
   - exact GraphQL declaration used by each read path
   - exact projection event family for each protocol step
   - exact projection read model for each product truth
   - exact live-query read still used by product truth
   - exact duplicated truth between contract service, projection, and frontend cache
   - exact missing truth for pending, failed, stalled, claimable, and claiming workflows
   - exact `webui-v2` components that must change for unified claim
   - exact service/kline projection/query files that must change for unified claim
   - exact generated GraphQL references used as dependency facts
   - exact audited GraphQL declaration files under `webui-v2/src/graphql/*.ts`
   - exact baseline tests needed before changing product truth
10. Required non-goals:
   - obsolete `webui/` is excluded from every product-truth audit row
   - generated GraphQL files under `webui-v2/src/__generated__/graphql/` are excluded from every audit row
   - Quasar framework files remain excluded
   - frontend product truth must not be inferred from page text alone
   - projection truth must not be inferred from contract state names alone

### Gate 1C Acceptance Criteria

Gate 1C is accepted only if:

1. `CreateMeme` is represented as a fixed multi-step protocol path.
2. `Meme Mining / Redeem` is represented as a fixed protocol path.
3. `Meme InitializeLiquidity` is represented as a fixed cross-contract protocol path.
4. `User CreatePool With Initial Liquidity` is represented as a fixed multi-step protocol path.
5. `AddLiquidity Funding` is represented as a fixed protocol path.
6. `Swap Funding And Settlement` is represented as a fixed protocol path.
7. `RemoveLiquidity Funds Exit` is represented as a fixed protocol path.
8. `Unified Claim Target Gap` is represented as a fixed audit path.
9. `Tracked Reject / Bounce Gap` is represented as a fixed audit path.
10. `Projection And Product Truth` is represented as a fixed cross-cutting audit path.
11. Gate 2 must audit whether meme `Redeem` remains a meme-local balance exit or must converge into the unified `Claim` model.

## Gate 1D Exclusions

Gate 2 must not audit excluded implementation files, modify excluded implementation
files, cite excluded implementation files as current implementation truth, or use
excluded implementation files as task-scope evidence.

### Gate 1D Excluded Frontend Paths

1. Obsolete frontend:
   - `webui/`
2. Generated frontend GraphQL output:
   - `webui-v2/src/__generated__/graphql/`
3. Quasar framework files:
   - `webui-v2/quasar.config.ts`
   - `webui-v2/src/boot/axios.ts`
   - `webui-v2/src/boot/i18n.ts`
   - `webui-v2/src/boot/notify-defaults.ts`
   - `webui-v2/src/boot/pinia.ts`
4. Frontend build and dependency outputs:
   - `webui-v2/dist/`
   - `webui-v2/.quasar/`
   - `webui-v2/node_modules/`

### Gate 1D Excluded Build, Cache, And Tool Outputs

1. Rust build output:
   - `target/`
2. Python cache and test cache outputs:
   - `__pycache__/`
   - `.pytest_cache/`
3. Package-manager cache outputs:
   - `.bun/`
   - `.yarn/`
   - `.pnpm-store/`

### Gate 1D Excluded Task And Evidence Sources

1. Human-facing documents as task truth:
   - `documents/`
2. Files absent from Gate 1B:
   - every repository file not listed under `Gate 1B In-Scope Files` when used as Gate 2 current implementation audit evidence
3. Directory-only audit evidence:
   - any Gate 2 finding that cites only a directory path without a concrete Gate 1B file path

### Gate 1D Excluded Semantic Objects

1. Non-funding claim semantics:
   - `AmsOperation::Claim`
   - `AmsMessage::Claim`
   - Linera chain claim
2. Protocol workflows outside Gate 1C:
   - every workflow not represented by one of the 10 accepted Gate 1C paths

### Gate 1D Rules

1. `webui/` is obsolete legacy code. Gate 2 must not read `webui/` as current frontend truth.
2. `webui-v2/` is the only current frontend for Gate 2.
3. Generated GraphQL files under `webui-v2/src/__generated__/graphql/` are build outputs. Gate 2 may mention them only as dependency facts and must not audit them as source files.
4. Audited frontend GraphQL declarations remain limited to concrete files listed under `Gate 1B Layer 6 Product Entry And Truth Boundary Files`.
5. Quasar framework files listed in this Gate 1D section must not be audited or modified by Gate 2.
6. `documents/` is not a task source and is not Gate 2 current implementation audit evidence. When the user explicitly requests human-facing documentation, `documents/` may be written under project rules, but it must not become Gate 2 task truth or audited implementation evidence.
7. Gate 2 must not merge AMS claim semantics, Linera chain claim semantics, and target funding `Claim`.
8. Gate 2 findings must cite concrete Gate 1B file paths.
9. Gate 2 must not audit files absent from Gate 1B.
10. Gate 2 may update `agents/tasks/board.yaml`, `agents/tasks/prompt-state.yaml`, and this primitive under project rules for task routing, status, and scope-freeze maintenance, but those files are not current implementation audit evidence.
11. Gate 2 must not introduce protocol paths outside the accepted Gate 1C paths.
12. Cross-cutting observations must attach to one accepted Gate 1C path, `Unified Claim Target Gap`, `Tracked Reject / Bounce Gap`, or `Projection And Product Truth`.

### Gate 1D Acceptance Criteria

Gate 1D is accepted only if:

1. Every exclusion has an explicit file path, directory path, object name, or semantic boundary.
2. No exclusion uses expandable wording such as `related`, `as needed`, `etc`, or similar open-ended terms.
3. `webui/` is fully excluded from current frontend analysis, funding scope, frontend constraints, implementation, tests, task plans, and assistant primitives.
4. `webui-v2/` remains the only current frontend.
5. Generated GraphQL files under `webui-v2/src/__generated__/graphql/` are excluded without weakening the audited `webui-v2/src/graphql/*.ts` declaration scope fixed by Gate 1B.
6. Quasar framework files are excluded without weakening audited `webui-v2/` product-entry, store, wallet, protocol utility, GraphQL declaration, projection transport, and worker scope fixed by Gate 1B.
7. AMS `Claim` and Linera chain claim remain excluded from FUND-005 funding `Claim`.
8. Gate 2 cannot cite excluded files as audited evidence.
9. Gate 2 cannot cite directory-only findings as audited evidence.
10. Gate 2 cannot add protocol paths outside the accepted Gate 1C path list.

## Gate 1E Audit Dimensions And Gate 2 Format Constraints

Gate 2 must use the audit dimensions and output format fixed in this section.
Gate 2 must produce an audit table, not a prose report.

### Gate 1E Audit Dimensions

Each Gate 2 audit row must answer these dimensions:

1. Layer
   - must be exactly one of the seven Gate 1A layers
2. Path
   - must be exactly one of the 10 Gate 1C paths
   - cross-cutting rows must attach to `Unified Claim Target Gap`, `Tracked Reject / Bounce Gap`, or `Projection And Product Truth`
3. File
   - must be one concrete Gate 1B file path
   - must not be a directory path
   - must not be a Gate 1D excluded path
   - for rows with `status = excluded`, must be `excluded:<exact Gate 1D excluded path or object>`
4. Symbol
   - must be one concrete operation, message, handler, function, state method, service query, projection object, frontend entry, or frontend helper symbol
   - must identify one primary symbol
   - may include direct protocol entry or callee symbols from other Gate 1B files when the row needs both an ABI object and its implementation entry
   - must annotate each additional direct protocol entry or callee symbol with its concrete Gate 1B file path
   - must not be a generic term such as `handler`, `state`, `frontend`, or `service`
5. Current behavior
   - must describe what the current implementation does
   - must be derived from the Gate 1B file named in the same row
6. Current state reads
   - must list current state, runtime, service query, frontend store, GraphQL declaration, or projection truth reads
   - must use `none` when the row has no current reads
7. Current state writes
   - must list current state, projection, cache, outgoing message, outgoing operation, or transfer writes
   - must use `none` when the row has no current writes
8. Economic effect
   - must list native transfer, meme transfer, mint, burn, LP mint, LP burn, reserve mutation, claim balance, claiming balance, refund, payout, fee-budget funding, open-chain balance, application creation, chain opening, permission change, transaction fact, or `none`
9. Source and auth checks
   - must list current source-chain, authenticated-signer, authenticated-caller, message-origin, application-id, owner, recipient, and runtime-context checks
   - must use `missing` when a required check is absent
10. Identity and amount checks
   - must list current token identity, pool identity, application identity, intent identity, workflow identity, transfer id, leg, amount, min amount, and slippage checks
   - must use `missing` when a required check is absent
11. Terminal truth
   - must identify where current success, fail, pending, stale, duplicate, bounced, and rejected truth is stored or observed
   - must use `missing` when no current terminal truth exists
12. Target delta
   - must state the gap against accepted funding target design
   - must use `none` when current behavior is aligned with target design
13. Required tests
   - must list current test files that already lock the behavior
   - must list concrete missing characterization tests
   - must use `none` only when existing tests fully cover the row
14. Product truth
   - must state whether product truth comes from contract state, contract service, live GraphQL query, service/kline projection, frontend cache, generated GraphQL dependency fact, or `none`
   - must identify duplicated truth when more than one product truth source exists

### Gate 1E Gate 2 Required Columns

Gate 2 audit output must use exactly these columns in this order:

1. `id`
2. `layer`
3. `path`
4. `file`
5. `symbol`
6. `current_behavior`
7. `current_state_reads`
8. `current_state_writes`
9. `economic_effect`
10. `source_and_auth_checks`
11. `identity_and_amount_checks`
12. `terminal_truth`
13. `target_delta`
14. `required_tests`
15. `product_truth`
16. `status`

### Gate 1E Status Values

The `status` column must contain one or more of these values:

1. `aligned`
2. `current_gap`
3. `target_gap`
4. `test_gap`
5. `excluded`

`excluded` must be used alone. `excluded` must not be combined with `aligned`,
`current_gap`, `target_gap`, or `test_gap`.
`aligned` must be used alone. `aligned` must not be combined with `current_gap`,
`target_gap`, `test_gap`, or `excluded`.
Only `current_gap`, `target_gap`, and `test_gap` may be combined with each other.

### Gate 1E Format Rules

1. Each row must cite exactly one Gate 1A layer.
2. Each row must cite exactly one Gate 1C path.
3. Each non-excluded row must cite exactly one concrete Gate 1B file path.
4. Each excluded row must set `file` to `excluded:<exact Gate 1D excluded path or object>`.
5. Each row must cite exactly one primary symbol.
6. Each row may include direct protocol entry or callee symbols from other Gate 1B files only when each additional symbol is annotated with its concrete Gate 1B file path.
7. Rows with `status = excluded` may identify a Gate 1D excluded item but must not use it as current implementation evidence.
8. Rows with `status = aligned` must not include `current_gap`, `target_gap`, `test_gap`, or `excluded`.
9. Rows with `status = excluded` must not include `aligned`, `current_gap`, `target_gap`, or `test_gap`.
10. Rows may combine only `current_gap`, `target_gap`, and `test_gap`.
11. Rows must not use expandable or ambiguous wording such as `related`, `as needed`, `etc`, `maybe`, `unclear`, `basically`, or similar terms.
12. Rows must not use `or` to express ambiguous alternative facts, alternative scopes, alternative paths, alternative files, alternative symbols, alternative checks, alternative tests, or alternative truth sources.
13. Rows may use `or` when it appears as part of an exact identifier, field name, enum name, file name, function name, status value, quoted source symbol, or ordinary English word that does not express an unresolved alternative.
14. Non-excluded rows must not cite directory paths as `file`.
15. Non-excluded rows must not cite `webui/`.
16. Non-excluded rows must not cite generated GraphQL files under `webui-v2/src/__generated__/graphql/` as audited files.
17. Rows must not treat `AmsOperation::Claim`, `AmsMessage::Claim`, or Linera chain claim as FUND-005 funding `Claim`.
18. Rows must not introduce protocol paths outside the accepted Gate 1C path list.
19. If current implementation has no terminal truth, `terminal_truth` must be `missing`.
20. If a required check is absent, the corresponding check column must include `missing`.
21. If current implementation has no tests for the row, `required_tests` must list concrete missing tests and must not say only `add tests`.
22. If a row depends on generated GraphQL output, `product_truth` must identify it as `generated GraphQL dependency fact`, and `file` must remain a Gate 1B GraphQL declaration file under `webui-v2/src/graphql/*.ts`.

### Gate 1E Acceptance Criteria

Gate 1E is accepted only if:

1. Gate 2 has fixed required columns and cannot be delivered as a free-form prose report.
2. Gate 2 rows can map directly to one Gate 1A layer, one Gate 1B file, and one Gate 1C path.
3. Gate 2 can represent current implementation gaps, target design gaps, and test gaps.
4. Gate 2 can represent combined current implementation, target design, and test gaps without duplicating audit rows.
5. Gate 2 keeps `aligned` rows and `excluded` rows mutually exclusive from gap rows.
6. Gate 2 can identify excluded items without turning excluded paths into current implementation evidence.
7. Gate 2 can cite direct protocol entry or callee symbols from Gate 1B files without overloading the primary `file` column.
8. Gate 2 explicitly forbids expandable or ambiguous wording.
9. Gate 2 explicitly forbids ambiguous `or` alternatives while permitting `or` inside exact identifiers and non-alternative words.
10. Gate 2 explicitly forbids Gate 1D excluded paths from becoming current implementation evidence.
11. Gate 2 explicitly preserves `webui-v2/src/graphql/*.ts` as audited GraphQL declaration scope while excluding generated GraphQL output.
12. Gate 2 explicitly requires `missing` for absent terminal truth and absent required checks.
13. Gate 2 explicitly requires concrete missing test descriptions when tests are absent.
14. Gate 2 can be used directly as the Gate 2 audit-table contract without adding another format explanation.
