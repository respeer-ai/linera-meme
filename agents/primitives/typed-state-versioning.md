# Typed State Versioning

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Record the canonical upgradeable-state architecture for business applications.

This primitive supersedes the generic BCS-bytes state application as the default business-state model.

## Status

- Design only until a task explicitly enters implementation.
- Do not implement ABI or contract changes from this document without user review.
- For ABI and contract changes, first discuss the shape, then provide a diff for review before applying.
- Every code diff must be small enough for review; target at most 50 changed lines per diff.
- If a proposed code diff exceeds 50 changed lines, split it into smaller review steps before applying.
- Review tasks may produce diff text only; do not apply the diff until the user explicitly approves it.

## Target Model

Each business application uses append-only typed state application versions:

```text
BusinessAppV1
  -> BusinessStateV1

BusinessAppV2
  -> BusinessStateV1
  -> BusinessStateV2

BusinessAppV3
  -> BusinessStateV1
  -> BusinessStateV2
  -> BusinessStateV3
```

`BusinessStateVx` is a concrete typed state application for one business domain. It is not a generic key/value state app and does not store business values as `Vec<u8>`.

The generic BCS-bytes state app is not part of the main business-state architecture.

## Hard Rules

- Do not migrate historical data.
- Do not copy records from old state versions into new state versions.
- Do not delete old state versions.
- Do not overwrite old state bindings.
- New fields and correction records are represented by appending a new typed state version.
- A correction is an explicit new record in a later state version; it does not mutate the original historical record.
- `AppendState` never accepts a version argument from the user.
- Code review diffs must stay within 50 changed lines by default; split larger changes.
- Business code versions must require an exact latest state version, never `>=`.
- Handlers do not receive state application ids, state versions, or patch details.
- Business adapters own version routing and multi-state composition.

## Package Boundary

Typed business app and typed state app implementations are separate Rust packages and separate Linera applications.

For AMS, use this package shape:

```text
ams/app     # business app package
ams/state   # typed StateV1 package
```

Dependency direction:

```text
ams-app   -> abi, runtime, base, linera-sdk
ams-state -> abi, runtime, base, linera-sdk

ams-app   -X-> ams-state
ams-state -X-> ams-app
```

Rules:

- Business app code must not import typed state app implementation modules.
- Typed state app code must not import business app implementation modules.
- Cross-application calls use only `abi::ams::state_v1` ABI types and runtime application calls.
- Shared implementation code is allowed only when it belongs in `abi`, `runtime`, or `base`.
- Do not use one `ams` library target to expose both app and state implementation modules.

## Business App Local State

Each business app stores state versions append-only:

```rust
state_versions: MapView<u16, ApplicationId>
latest_state_version: RegisterView<u16>
```

The app code declares the exact layout it supports:

```rust
const EXPECTED_LATEST_STATE_VERSION: u16 = N;
```

Normal business handlers must require:

```text
latest_state_version == EXPECTED_LATEST_STATE_VERSION
state_versions[1..=EXPECTED_LATEST_STATE_VERSION] all exist
required bootstrap records exist in the relevant state versions
```

Never use:

```text
latest_state_version >= EXPECTED_LATEST_STATE_VERSION
```

## Business App Operations

Business apps provide these maintenance operations:

```rust
AppendState {
    state_application_id: ApplicationId,
}

Handoff {
    new_business_application_id: ApplicationId,
}
```

`AppendState` computes the next version internally:

```text
next_version = latest_state_version + 1
state_versions[next_version] = state_application_id
latest_state_version = next_version
```

`AppendState` constraints:

- Only governance/operator maintenance can call it.
- It only appends.
- It cannot overwrite an existing version.
- It cannot delete an old version.
- It rejects a state application id that is already present.
- It does not migrate, copy, or initialize historical records.

Typed state app initialization happens in typed state app instantiate when the required binding and initial records are known at deployment time. Do not add a no-op `Bootstrap` lifecycle only to mirror older generic-state flows.

## Typed State App Model

Each typed state app serves exactly one business app instance and one state version.

It stores:

```rust
business_application_id: RegisterView<ApplicationId>
typed_business_records: ...
```

It does not have:

```text
namespace
slot
BindApplication
bound_applications
generic bytes records
generic freeze/unfreeze
```

If a chain needs two independent business app instances, deploy two independent state app instances. Do not multiplex instances inside one state app.

## Typed State App Instantiation

State app instantiate binds it to the authorized business app:

```rust
StateInstantiationArgument {
    business_application_id: ApplicationId,
}
```

An operator may be included only if that concrete state app needs an independent maintenance operator. The default architecture keeps maintenance orchestration in the business app.

## Read And Write Authorization

Reads are open:

```text
Read*: no caller authorization
```

Writes require:

```text
authenticated_caller_application_id == business_application_id
runtime.chain_id() == creator_chain_id(authenticated_caller_application_id)
```

The state app needs runtime capabilities for:

```text
authenticated_caller_application_id()
chain_id()
creator_chain_id(application_id)
```

The creator-chain check ensures the authorized business app writes state only on its creator chain.

## State App Handoff

Each typed state app provides:

```rust
Handoff {
    new_business_application_id: ApplicationId,
}
```

`Handoff` is a write-class maintenance operation. It must require:

```text
authenticated_caller_application_id == current business_application_id
runtime.chain_id() == creator_chain_id(current business_application_id)
runtime.chain_id() == creator_chain_id(new_business_application_id)
```

On success it only updates:

```text
business_application_id = new_business_application_id
```

It does not move, copy, rewrite, or migrate business records.

The `new_business_application_id` must have the same creator chain as the state app chain. Otherwise the handoff would bind the state app to a business app that cannot continue writing the existing state records on the state app chain.

## First Deploy Flow

First deploy must obtain the business app id before creating its state app:

```text
1. Deploy BusinessApp shell with no state ids.
2. Obtain BusinessApp id.
3. Deploy BusinessStateV1 with business_application_id = BusinessApp id.
4. Call BusinessApp.AppendState(StateV1 id).
5. Start normal operations only when the exact expected state version exists.
```

Business app instantiate does not call a state app and does not initialize business records.

## Upgrade Without New State

For:

```text
BusinessAppV1 -> StateV1
BusinessAppV2 -> StateV1
```

Flow:

```text
1. Deploy BusinessAppV2 shell.
2. Call BusinessAppV2.AppendState(StateV1 id).
3. Call BusinessAppV1.Handoff(BusinessAppV2 id).
4. BusinessAppV1 calls StateV1.Handoff(BusinessAppV2 id).
5. BusinessAppV2 can use StateV1; BusinessAppV1 can no longer write StateV1.
```

No records move.

## Upgrade With New State

For:

```text
BusinessAppV1 -> StateV1
BusinessAppV2 -> StateV1 + StateV2
```

Flow:

```text
1. Deploy BusinessAppV2 shell.
2. Call BusinessAppV2.AppendState(StateV1 id).
3. Deploy StateV2 with business_application_id = BusinessAppV2 id.
4. Call BusinessAppV2.AppendState(StateV2 id).
5. Call BusinessAppV2.Bootstrap for StateV2 required records.
6. Call BusinessAppV1.Handoff(BusinessAppV2 id).
7. BusinessAppV1 hands off only old owned states, such as StateV1.
8. BusinessAppV2 composes reads from StateV1 and StateV2.
```

StateV2 is owned by the new app from creation and does not participate in the old app's handoff.

## Adapter Routing

The business adapter maps each field to a state version:

```text
old_field       -> read/write StateV1
new_field       -> read/write StateV2
corrected_field -> read StateV1 base + read StateV3 correction + apply deterministic rule
```

Do not implement implicit migration:

```text
read StateV2
if missing:
  read StateV1
  write StateV2
```

Allowed correction pattern:

```text
base = read StateV1
correction = read StateV3
return apply_correction(base, correction)
```

## Atomicity Requirements

Business `Handoff` may call multiple old state apps:

```text
StateV1.handoff(new_app)
StateV2.handoff(new_app)
```

The implementation must test same-transaction `call_application` rollback semantics. If one state handoff fails, no previous state handoff may remain committed. If Linera does not provide the required rollback behavior for this flow, introduce a reviewed two-phase handoff design before implementation.

The same atomicity requirement applies to normal business operations that write multiple state versions.

## Testing Requirements

Typed state app tests:

- instantiate stores the authorized `business_application_id`
- reads are open
- authorized creator-chain writes succeed
- non-authorized app writes fail
- authorized app writes from a non-creator chain fail
- handoff preserves all records
- old app writes fail after handoff
- handoff rejects a new app whose creator chain differs from the state app chain
- new app writes succeed on the shared creator chain after handoff

Business app tests:

- shell instantiate has empty state versions and does not call state apps
- `AppendState` auto-increments versions and rejects duplicates
- no user-supplied version exists
- normal handlers require exact `EXPECTED_LATEST_STATE_VERSION`
- handler code does not know state app ids or versions
- adapter routes fields to fixed versions
- no migration operation or fallback-write migration exists
- business handoff calls all old owned states and not newly created states

Multi-chain tests:

- first deploy: shell, StateV1, `AppendState`, normal business operation, service read
- upgrade without new state: old writes, new shell, append old StateV1, old handoff, new reads old data, old write rejected
- upgrade with new state: append StateV1, create/append StateV2, bootstrap StateV2, handoff StateV1, compose V1+V2
- multi-state handoff success
- partial handoff failure rollback
- creator-chain write authorization

## Rollout

Do not migrate every business app at once.

First validate the architecture with AMS:

```text
AmsAppV1 -> AmsStateV1
AmsAppV2 -> AmsStateV1
AmsAppV3 -> AmsStateV1 + AmsStateV2
```

After AMS first deploy, upgrade, no-migration, and multi-chain tests pass, evaluate Proxy, Meme, Pool, and Swap individually. Meme, Pool, and Swap require dedicated key/value granularity and read-count design before implementation.
