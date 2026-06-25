# State Application

Type: Primitive
Audience: Coding assistants
Authority: Medium

## Purpose

Record the current design for the reusable `state` application shared by upgradeable business applications.

## Status

- Design only
- Do not implement from this document without a task that explicitly enters implementation
- This document is the canonical assistant-facing design for the `state` application

## Facts

- Current `meme`, `proxy`, `swap`, and `pool` contracts keep protocol state inside their own application state
- Recreating an application creates a new application identity and an empty application state replica
- A business application can call a state application on the same chain with authenticated `call_application`
- Runtime authenticated caller id identifies the calling application during an authenticated application call
- Runtime authenticated signer identifies the signed account owner for operator operations
- Linera cross-chain messages are application-local messages; a state application does not send business application messages
- The `state` application is deployed once as an application id and reused on many chains
- Each chain has its own state application replica
- The implementation crate is `state`
- The application ABI module is `abi::state`
- The root view type is named `State`
- The state app contract type is `StateContract`
- The state app service type is `StateService`
- Business-facing state interfaces are traits under `state::interfaces`
- Business-facing concrete state app request instances are under `state::adapters`

## Target Model

- One `state_app_id` is reused by many business chains
- Each business chain stores its business state in that chain's state application replica
- The `state` application is domain-blind
- The `state` application does not know about `meme`, `proxy`, `swap`, `pool`, AMM math, mining, or token rules
- Business applications define typed key schemas, value schemas, invariants, services, and user-facing APIs
- Users and frontends query business applications or off-chain services, not the raw `state` application
- The `state` service may expose raw debug/admin reads only

## Repository Shape

- Add workspace member `state`
- Add ABI module `abi/src/state.rs`
- Add `pub mod state;` to `abi/src/lib.rs`
- Add `state` to the workspace member list in root `Cargo.toml`
- Add `state.workspace = true` to root `Cargo.toml` workspace dependencies only if another crate must import the implementation crate
- Prefer business crates importing `abi::state::{StateAbi, StateOperation, StateResponse}` over importing the implementation crate
- Use Cargo dependency rename only when a business crate must import the implementation crate and has a local `state` module:
  ```toml
  state-app = { package = "state", path = "../state" }
  ```
- Do not name the crate `generic-state`

Required implementation shape follows the existing application crate pattern used by `ams` and other business applications:

```text
state/Cargo.toml
state/src/lib.rs
state/src/adapters.rs
state/src/adapters/contract.rs
state/src/adapters/service.rs
state/src/state.rs
state/src/state/adapter.rs
state/src/state/errors.rs
state/src/state/state_impl.rs
state/src/interfaces.rs
state/src/interfaces/state.rs
state/src/interfaces/contract.rs
state/src/interfaces/service.rs
state/src/contract.rs
state/src/contract_impl.rs
state/src/contract_inner.rs
state/src/contract_inner/errors.rs
state/src/contract_inner/handlers.rs
state/src/contract_inner/handlers/operation.rs
state/src/service.rs
state/src/contract_tests.rs
state/src/contract_tests/contract.rs
```

Module responsibilities:

- `state/src/state.rs` defines the root view type `State` and declares `adapter`, `errors`, and `state_impl`
- `state/src/interfaces/state.rs` defines the internal state app `StateInterface`
- `state/src/state/state_impl.rs` implements the internal `StateInterface` for `State`
- `state/src/state/adapter.rs` wraps `Rc<RefCell<State>>` for state app contract handlers
- `state/src/interfaces/contract.rs` defines only the business-facing contract trait `StateContractInterface`
- `state/src/interfaces/service.rs` defines only the business-facing service trait `StateServiceInterface`
- `state/src/adapters/contract.rs` defines the concrete business-facing `StateContract` instance
- `state/src/adapters/service.rs` defines the concrete business-facing `StateService` instance
- `state/src/contract.rs` and `state/src/service.rs` remain the state app Linera entrypoints

Public business-facing paths:

```rust
state::interfaces::contract::StateContractInterface
state::interfaces::service::StateServiceInterface
state::adapters::contract::StateContract
state::adapters::service::StateService
```

Rules:

- `interfaces` contains trait contracts only
- `adapters` contains concrete trait implementations and runtime-backed instances
- Do not put concrete `StateContract` or `StateService` implementations under `state/src/interfaces`
- Do not use `client` or `access` in the business-facing state wrapper names

Required binary names:

```toml
[[bin]]
name = "state_contract"
path = "src/contract.rs"

[[bin]]
name = "state_service"
path = "src/service.rs"
```

## State Shape

```rust
struct State {
    operator: RegisterView<Option<Account>>,
    frozen_namespaces: RegisterView<bool>,
    namespace_apps: MapView<u8, Vec<ApplicationId>>,
    records: MapView<Vec<u8>, Vec<u8>>,
}
```

- The Rust type name is exactly `State`
- `frozen_namespaces` is one global boolean
- `frozen_namespaces` freezes namespace management capability
- `frozen_namespaces` does not freeze business records
- Do not model frozen state as `MapView<u8, bool>`
- Do not use a field named only `frozen`; the field name must show that namespace management is frozen
- `namespace` is `u8`
- `slot` is `u8`
- Record keys are encoded as `[namespace: u8][slot: u8][business_key...]`
- `slot` is the index of the caller application id in `namespace_apps[namespace]`
- `namespace_apps[namespace]` is append-only except for handoff replace-in-place
- Do not remove entries from `namespace_apps`
- Do not reorder entries in `namespace_apps`
- Do not add `StateDomain`
- Do not add `object_id` for the current design
- Do not add compare-and-set for the current design
- Do not use verbose string or hash namespaces when a compact `u8` namespace is enough

## Operation ABI

```rust
enum StateOperation {
    InitializeOperator,
    CreateNamespace {
        namespace: u8,
    },
    FreezeNamespace,
    UnfreezeNamespace,
    Handoff {
        namespace: u8,
        new_application_id: ApplicationId,
    },
    BatchRead {
        namespace: u8,
        keys: Vec<Vec<u8>>,
    },
    BatchWrite {
        namespace: u8,
        writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    },
    SetOperator {
        new_operator: Account,
    },
}
```

```rust
enum StateResponse {
    Ok,
    BatchRead(Vec<Option<Vec<u8>>>),
}
```

- `FreezeNamespace` and `UnfreezeNamespace` do not carry a namespace argument
- `FreezeNamespace` and `UnfreezeNamespace` affect namespace management capability as a whole
- `CreateNamespace` does not carry an application id
- The application id bound by `CreateNamespace` is always `authenticated_caller_id`
- `CreateNamespace` does not initialize the operator
- Operator initialization is only `InitializeOperator`
- `BatchRead` returns `StateResponse::BatchRead`
- `BatchWrite` and namespace management operations return `StateResponse::Ok`
- `StateAbi::Operation` is `StateOperation`
- `StateAbi::Response` is `StateResponse`
- `StateAbi::Query` is `async_graphql::Request`
- `StateAbi::QueryResponse` is `async_graphql::Response`

## Internal State Interface

The state app itself uses the same interface-driven structure as existing application crates.

`state/src/interfaces/state.rs` defines the state app internal `StateInterface`.

Required shape:

```rust
#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error>;
    async fn create_namespace(&mut self, namespace: u8) -> Result<(), Self::Error>;
    async fn freeze_namespace(&mut self) -> Result<(), Self::Error>;
    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error>;
    async fn handoff(
        &mut self,
        namespace: u8,
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;
    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;
    async fn batch_read(
        &mut self,
        namespace: u8,
        keys: Vec<Vec<u8>>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error>;
    async fn batch_write(
        &mut self,
        namespace: u8,
        writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    ) -> Result<(), Self::Error>;
}
```

Rules:

- State app contract handlers depend on `S: state::interfaces::state::StateInterface`
- State app contract handlers do not directly manipulate `State`
- `state::state::adapter::StateAdapter` wraps `Rc<RefCell<State>>` and implements the internal `StateInterface`
- The internal `StateInterface` is for the state app implementation only; business apps do not implement it

## InitializeOperator

`InitializeOperator` initializes an empty state replica operator.

Rules:

1. Require `authenticated_signer`
2. Require `operator == None`
3. Store:
   ```rust
   operator = Account {
       chain_id: runtime.chain_id(),
       owner: authenticated_signer,
   }
   ```
4. Do not accept an operator payload
5. Reject repeated initialization

Implications:

- The first business application initialization path must call `InitializeOperator` before using namespace management operations
- This makes the current chain signer the state operator for that chain's state application replica
- `FreezeNamespace`, `UnfreezeNamespace`, and `SetOperator` cannot run before operator initialization

## CreateNamespace

`CreateNamespace` binds the authenticated caller application to a namespace.

Rules:

1. Require `operator != None`
2. Require authenticated same-chain application call
3. Read `caller = authenticated_caller_id`
4. Require `caller.creator_chain_id == runtime.chain_id()`
5. Require `frozen_namespaces == false`
6. Require `namespace_apps[namespace]` does not already contain `caller`
7. Append `caller` to `namespace_apps[namespace]`

Do not:

- Do not accept an application id payload
- Do not bind any application id other than `authenticated_caller_id`
- Do not silently no-op on duplicate binding
- Do not check `change_application_permissions.contains(caller)` in the current design; pool and meme register themselves during their existing initialization paths

## Read And Write

`BatchRead` and `BatchWrite` access business records.

Rules:

1. Require `authenticated_caller_id`
2. Require caller exists in `namespace_apps[namespace]`
3. Compute `slot` as caller's index in `namespace_apps[namespace]`
4. Access records at `[namespace][slot][business_key...]`
5. Ignore `frozen_namespaces`

Implications:

- Frozen namespace management still allows normal business reads and writes
- Business applications can only read and write records under their namespace slot
- Business applications own typed key/value encoding and decoding

## FreezeNamespace And UnfreezeNamespace

`FreezeNamespace` and `UnfreezeNamespace` control namespace management capability.

Rules:

1. Require `authenticated_signer`
2. Construct `actual = Account { chain_id: runtime.chain_id(), owner: authenticated_signer }`
3. Require `actual == operator`
4. `FreezeNamespace` sets `frozen_namespaces = true`
5. `UnfreezeNamespace` sets `frozen_namespaces = false`

When `frozen_namespaces == true`:

- Allow `BatchRead`
- Allow `BatchWrite`
- Reject `CreateNamespace`
- Reject `Handoff`
- Reject `SetOperator`

## Handoff

`Handoff` replaces the bound application id in-place for an upgrade.

Rules:

1. Require authenticated application call
2. Require `frozen_namespaces == false`
3. Require caller exists in `namespace_apps[namespace]`
4. Require `new_application_id.creator_chain_id == caller.creator_chain_id`
5. Require `new_application_id` is not already bound in `namespace_apps[namespace]`
6. Replace caller's existing slot with `new_application_id`

Do not:

- Do not let the new application call `Handoff`
- Do not append during handoff
- Do not change slot
- Do not let the `state` application validate business governance

Business application responsibility:

- The old active business application validates operator, governance, quorum, target app identity, and upgrade policy before calling `Handoff`

## SetOperator

`SetOperator` rotates the state operator.

Rules:

1. Require `frozen_namespaces == false`
2. Require current operator signer
3. Require `new_operator.chain_id == runtime.chain_id()`
4. Store `new_operator`

## Business Application State

Business applications store only minimal local binding required to reach the `state` application.

Required local fields:

```rust
state_app_id: RegisterView<Option<ApplicationId<StateAbi>>>,
state_namespace: RegisterView<Option<u8>>,
```

Rules:

- Do not put mutable `state_app_id` in immutable parameters
- Business app parameters may identify immutable construction inputs only
- Business apps define all typed business keys and values
- Business key enums live in each business ABI module, such as `abi/src/meme.rs`, `abi/src/pool.rs`, and `abi/src/swap.rs`
- Do not add a shared business `state/key` module for key schemas
- Business apps do not repeat raw BCS encode/decode at every call site; state adapters perform typed BCS encode/decode behind their interfaces

## Business-Facing State Interfaces And Adapters

The `state` crate provides interface traits and concrete runtime-backed instances for business applications.

`state/src/interfaces/contract.rs` contains only `StateContractInterface`.

Required contract-side interface shape:

```rust
#[async_trait(?Send)]
pub trait StateContractInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error>;
    async fn create_namespace(&mut self) -> Result<(), Self::Error>;
    async fn freeze_namespace(&mut self) -> Result<(), Self::Error>;
    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error>;
    async fn handoff(&mut self, new_application_id: ApplicationId) -> Result<(), Self::Error>;
    async fn read<K, V>(&mut self, key: &K) -> Result<Option<V>, Self::Error>;
    async fn batch_read<K, V>(&mut self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>;
    async fn write<K, V>(&mut self, key: &K, value: &V) -> Result<(), Self::Error>;
    async fn batch_write<K, V>(&mut self, writes: &[(K, Option<V>)]) -> Result<(), Self::Error>;
    async fn delete<K>(&mut self, key: &K) -> Result<(), Self::Error>;
}
```

`state/src/adapters/contract.rs` contains `StateContract`, the concrete implementation of `StateContractInterface`.

`StateContract` stores the runtime wrapper, `state_app_id`, and `namespace` at construction time. Business methods pass only business keys and values.

Rules:

- `StateContract` wraps `call_application` and `StateOperation` construction
- `StateContract` performs typed BCS encode/decode for key/value helpers
- `StateContract` does not implement business invariants
- Business app handlers do not depend on `StateContract` directly; they depend on their own business `StateInterface`
- Business app state adapters may depend on `C: state::interfaces::contract::StateContractInterface`

`state/src/interfaces/service.rs` contains only `StateServiceInterface`.

Required service-side interface shape:

```rust
#[async_trait(?Send)]
pub trait StateServiceInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn read<K, V>(&self, key: &K) -> Result<Option<V>, Self::Error>;
    async fn batch_read<K, V>(&self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>;
}
```

`state/src/adapters/service.rs` contains `StateService`, the concrete implementation of `StateServiceInterface`.

Rules:

- `StateService` wraps `query_application` against the state app service
- `StateService` is read-only and does not expose write, delete, handoff, or operator mutation methods
- Service mutations still schedule business app operations; they do not write the state app directly
- Business service query wrappers may depend on `S: state::interfaces::service::StateServiceInterface`

## State Key Encoding

The `state` crate provides the common key trait used by typed helpers:

```rust
pub trait StateKey {
    fn to_state_key(&self) -> Vec<u8>;
}
```

Business ABI modules define business key enums and implement `StateKey`.

Examples:

```text
abi/src/meme.rs -> MemeKey
abi/src/pool.rs -> PoolKey
abi/src/swap.rs -> SwapKey
```

Rules:

- Key schemas are protocol layout and belong with each business ABI
- The `state` app never matches on business key variants
- The `state` app only stores raw business key bytes after namespace and slot prefixing

## Service Queries

There are two distinct service concepts:

- `state/src/service.rs` is the state app service entrypoint for raw debug/admin inspection
- `state::adapters::service::StateService` is a business-facing read-only instance that queries the state app from a business service

The state app service entrypoint may expose typed GraphQL fields only for state-app administration facts:

- `operator`
- `frozenNamespaces`
- `namespaceApps(namespace)`
- raw record lookup by exact encoded key or by `(namespace, slot, business_key)`

Rules:

- Do not decode business records in the state app service entrypoint
- Do not expose user-facing pool, meme, swap, mining, balance, or position queries from the state app service entrypoint
- Do not make frontend routing depend on the state app service entrypoint
- Business service GraphQL resolvers query business methods or business read-only wrappers, not raw state app records directly
- Business service code does not force the full write-capable business `StateInterface`; use a business read-only query interface or query wrapper because service runtime is read-only

## Business Application Integration Pattern

Business contract handlers keep the existing dependency shape:

```rust
R: ContractRuntimeContext + AccessControl
S: BusinessStateInterface
```

Handlers do not know the state app exists. They do not pass `state_app_id`, do not pass `namespace`, and do not perform BCS encoding.

Business contract state adapters own the state app dependency:

```text
Business StateAdapter<C>
  -> Rc<RefCell<BusinessState>>
  -> C: state::interfaces::contract::StateContractInterface
```

Runtime entrypoints construct concrete instances and inject them:

```text
state::adapters::contract::StateContract
  -> business StateAdapter<C>
  -> business handler
```

Rules:

- Business `StateInterface` remains a business semantic interface such as `balance_of`, `transfer`, `approve`, and `mining_info`
- Business invariants remain in the business crate
- Business state implementation replaces local view reads/writes with calls through `StateContractInterface`
- Do not add a repository layer between business state implementation and the state adapter

Service-side integration is read-only:

```text
Business service query wrapper<S>
  -> S: state::interfaces::service::StateServiceInterface
```

Rules:

- Do not force service code to implement or consume the full write-capable business `StateInterface`
- A business crate may split a read-only business query interface from its write-capable `StateInterface`
- Contract code may use the full business `StateInterface`; service GraphQL code uses business read-only methods or wrappers

## Rc RefCell Borrowing

Business contract adapters must avoid holding a `RefCell` borrow across an async state app call.

Required pattern:

1. Short-borrow local binding or immutable local configuration
2. Release the borrow
3. Call `StateContractInterface` methods
4. Short-borrow again only if local state must be updated

Do not call async state app access while a `RefCell` borrow from `Rc<RefCell<BusinessState>>` is still live.

## Pool Creation Flow

Do not add a new `PostInitialize` stage.

Required sequence:

1. Swap creates the pool chain and pool application through the existing flow
2. Pool application runs its existing instantiate path
3. Pool application stores `state_app_id` and `state_namespace = NS_POOL` in minimal local state
4. Pool application calls state `InitializeOperator`
5. Pool application calls state `CreateNamespace { namespace: NS_POOL }`
6. Pool application calls state `BatchWrite` for initial pool business records
7. Existing swap `PoolCreated` flow continues
8. If the pool chain later opens to untrusted proposers, the state operator must run `FreezeNamespace` before opening

## Meme Creation Flow

Do not add a new `PostInitialize` stage.

Required sequence:

1. Proxy creates the meme chain and meme application through the existing flow
2. Meme application runs its existing instantiate/create path
3. Meme application stores `state_app_id` and `state_namespace = NS_MEME` in minimal local state
4. Meme application calls state `InitializeOperator`
5. Meme application calls state `CreateNamespace { namespace: NS_MEME }`
6. Meme application calls state `BatchWrite` for initial meme business records
7. State operator runs `FreezeNamespace` on the meme chain
8. Meme application verifies `frozen_namespaces == true`
9. Meme application opens mining / multi-leader rounds only after namespace management is frozen

## Upgrade Maintenance Window

Required sequence:

1. Business operator pauses mining or closes the business write entrypoint
2. Business operator tightens current-chain `application_permissions` to operator maintenance mode
3. Maintenance permissions remove open miner/user-triggered business entrypoints
4. Maintenance permissions keep only applications required for upgrade and permission changes
5. State operator runs `UnfreezeNamespace`
6. Deploy the new business application and obtain `new_application_id`
7. Old business application validates business governance and operator authorization
8. Old business application calls state `Handoff { namespace, new_application_id }`
9. Current-chain `application_permissions` replace old business app access with new business app access while staying in maintenance mode
10. State operator runs `FreezeNamespace`
11. Business operator restores runtime `application_permissions`
12. Business operator resumes mining or business writes

Rules:

- `UnfreezeNamespace` must happen only after the chain is in operator maintenance permissions
- Runtime permissions must not reopen before `FreezeNamespace` completes
- Open mining or untrusted proposers require `frozen_namespaces == true`

## Routing

- Do not add a chain registry application for this design
- Observability records facts and projections, not authoritative frontend routing
- Frontend must not hardcode root app ids
- Deployment tooling must update a dedicated deployment config service/interface with active root app ids
- Dynamic object identity must be stable outside application ids
- Active business app id can change through handoff

## Errors

Recommended error set:

```rust
enum StateError {
    MissingAuthenticatedCaller,
    MissingAuthenticatedSigner,
    OperatorNotInitialized,
    OperatorAlreadyInitialized,
    OperatorRequired,
    FrozenNamespaces,
    DuplicateApplicationBinding {
        namespace: u8,
        application_id: ApplicationId,
    },
    NamespaceNotFound {
        namespace: u8,
    },
    ApplicationNotBound {
        namespace: u8,
        application_id: ApplicationId,
    },
    HandoffTargetAlreadyBound {
        namespace: u8,
        application_id: ApplicationId,
    },
    InvalidCreatorChain {
        application_id: ApplicationId,
        expected: ChainId,
        actual: ChainId,
    },
    InvalidOperatorChain {
        expected: ChainId,
        actual: ChainId,
    },
}
```

## Rules

- Do not make the `state` application domain-aware
- Do not add `StateDomain`
- Do not add hard-coded `meme`, `proxy`, `swap`, or `pool` branches
- Do not put AMM math, token balance rules, mining rules, pool registry semantics, or operator quorum logic in the `state` application
- Do not use `required_application_ids` as a mutable upgrade registry
- Do not use the `state` application as a routing registry
- Do not add state app callbacks into business applications
- Do not make state app send business app messages
- Do not let business apps bind arbitrary application ids to namespaces
- Do not allow namespace management operations while `frozen_namespaces == true`
- Do not allow mining or untrusted proposers before `FreezeNamespace`
- Do not unfreeze namespace management before tightening chain application permissions into maintenance mode

## Validation

GSTATE-001 is complete only when tests cover:

- Repeated `InitializeOperator` rejects
- Missing signer rejects `InitializeOperator`, `FreezeNamespace`, `UnfreezeNamespace`, and `SetOperator`
- Non-operator signer rejects `FreezeNamespace`, `UnfreezeNamespace`, and `SetOperator`
- `CreateNamespace` rejects before operator initialization
- `CreateNamespace` rejects without authenticated caller
- `CreateNamespace` rejects caller from a different creator chain
- `CreateNamespace` rejects duplicate caller binding in the same namespace
- `frozen_namespaces == true` rejects `CreateNamespace`, `Handoff`, and `SetOperator`
- `frozen_namespaces == true` still allows `BatchRead` and `BatchWrite`
- `BatchRead` and `BatchWrite` reject unbound callers
- `BatchWrite` with `Some(bytes)` writes under `[namespace][slot][business_key...]`
- `BatchWrite` with `None` deletes only the caller slot record
- Separate namespaces isolate identical business keys
- Separate caller slots in the same namespace isolate identical business keys
- `Handoff` replaces in-place and preserves slot records
- `Handoff` rejects when called by the new app instead of the old app
- `Handoff` rejects a target already bound in the namespace
- `SetOperator` rejects a `new_operator` on a different chain
- `SetOperator` rotates operator and the old operator no longer authorizes namespace management
