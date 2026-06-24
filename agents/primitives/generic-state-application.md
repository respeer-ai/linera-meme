# Generic State Application

Type: Primitive
Audience: Coding assistants
Authority: Medium

## Purpose

Record the current design for a generic state application shared by upgradeable business applications.

## Status

- Design only
- Do not implement from this document without a task that explicitly enters implementation
- This document is the canonical assistant-facing design for the generic state application

## Facts

- Current `meme`, `proxy`, `swap`, and `pool` contracts keep protocol state inside their own application state
- Recreating an application creates a new application identity and an empty application state replica
- A business application can call a state application on the same chain with authenticated `call_application`
- Runtime authenticated caller id identifies the calling application during an authenticated application call
- Runtime authenticated signer identifies the signed account owner for operator operations
- Linera cross-chain messages are application-local messages; a state application does not send business application messages
- The generic state application is deployed once as an application id and reused on many chains
- Each chain has its own state application replica

## Target Model

- One generic `state_app_id` is reused by many business chains
- Each business chain stores its business state in that chain's state application replica
- The generic state application is domain-blind
- The generic state application does not know about `meme`, `proxy`, `swap`, `pool`, AMM math, mining, or token rules
- Business applications define typed key schemas, value schemas, invariants, services, and user-facing APIs
- Users and frontends query business applications or off-chain services, not the raw generic state application
- The generic state service may expose raw debug/admin reads only

## State Shape

```rust
struct State {
    operator: RegisterView<Option<Account>>,
    frozen_namespaces: RegisterView<bool>,
    namespace_apps: MapView<u8, Vec<ApplicationId>>,
    records: MapView<Vec<u8>, Vec<u8>>,
}
```

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

- `FreezeNamespace` and `UnfreezeNamespace` do not carry a namespace argument
- `FreezeNamespace` and `UnfreezeNamespace` affect namespace management capability as a whole
- `CreateNamespace` does not carry an application id
- The application id bound by `CreateNamespace` is always `authenticated_caller_id`
- `CreateNamespace` does not initialize the operator
- Operator initialization is only `InitializeOperator`

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
- Do not let generic state validate business governance

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

Business applications store only minimal local binding required to reach generic state.

Required local fields:

```rust
state_app_id: RegisterView<Option<ApplicationId<StateAbi>>>,
state_namespace: RegisterView<Option<u8>>,
```

Rules:

- Do not put mutable `state_app_id` in immutable parameters
- Business app parameters may identify immutable construction inputs only
- Business apps define all typed business keys and values
- Business apps decode state bytes for service/query responses

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

- Do not make the generic state application domain-aware
- Do not add `StateDomain`
- Do not add hard-coded `meme`, `proxy`, `swap`, or `pool` branches
- Do not put AMM math, token balance rules, mining rules, pool registry semantics, or operator quorum logic in generic state
- Do not use `required_application_ids` as a mutable upgrade registry
- Do not use generic state as a routing registry
- Do not add state app callbacks into business applications
- Do not make state app send business app messages
- Do not let business apps bind arbitrary application ids to namespaces
- Do not allow namespace management operations while `frozen_namespaces == true`
- Do not allow mining or untrusted proposers before `FreezeNamespace`
- Do not unfreeze namespace management before tightening chain application permissions into maintenance mode
