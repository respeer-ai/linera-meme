# Generic State Application

Type: Primitive
Audience: Coding assistants
Authority: Medium

## Purpose

Record the current design direction for separating immutable generic state applications from upgradeable business applications.

## Status

- Design discussion only
- Do not implement from this document without a task that explicitly enters implementation
- Open questions remain

## Facts

- Current `meme`, `proxy`, `swap`, and `pool` contracts keep protocol state inside their own application state
- Recreating an application creates a new application identity and an empty application state replica
- Linera `ApplicationDescription` includes `required_application_ids`
- Existing application descriptions are immutable; `required_application_ids` are set at application creation time
- A business application can call a state application on the same chain with authenticated `call_application`
- Runtime authenticated caller id identifies the calling application during an authenticated application call
- Runtime message origin and signer identify the cross-chain message source and authenticated operator account

## Target Model

- Split each upgradeable protocol object into:
  - one generic state application
  - one active business application
- The generic state application is not domain-specific
- The generic state application must not know about `meme`, `proxy`, `swap`, or `pool`
- The generic state application stores opaque bytes under opaque byte keys
- Business applications define typed key schemas, value schemas, invariants, and human-readable service APIs
- Users and frontend query business applications, not generic state applications
- Business application services decode state bytes and return typed, human-readable query results
- Generic state services may expose raw debug/admin reads only

## Generic State Responsibilities

- Store single-value records by opaque key
- Store map records by opaque map key plus opaque entry key
- Delete records
- Optionally support compare-and-set operations
- Store `active_business_app_id`
- Reject state writes from any caller other than `active_business_app_id`
- Support business application handoff from the current active business application to a new business application
- Keep upgrade mechanics generic and domain-independent

## Business Application Responsibilities

- Define typed state keys and typed state values
- Encode keys and values into bytes before calling the generic state application
- Decode bytes returned by the generic state application
- Enforce all business invariants
- Enforce operator authorization
- Enforce cross-chain message origin checks
- Enforce upgrade governance, quorum, and operator rotation rules
- Provide GraphQL/service query APIs with typed, human-readable responses
- Route users and product surfaces to the current active business application

## Upgrade Flow

1. A new business application is created on the same creator chain or object chain as required by the object.
2. The new business application is configured with the existing generic state application id.
3. An operator sends an upgrade request through the current active business application.
4. The current active business application checks message origin.
5. The current active business application authenticates the operator from runtime message signer/account facts.
6. The current active business application applies its governance, quorum, and rotation rules.
7. The current active business application calls the generic state application to hand off to the new business application.
8. The generic state application checks `authenticated_caller_id == active_business_app_id`.
9. The generic state application sets `active_business_app_id` to the new business application id.
10. Registry or routing state is updated so user/product calls target the new business application.

## Rules

- Do not make the generic state application domain-aware
- Do not add `StateDomain` or hard-coded `meme` / `proxy` / `swap` / `pool` branches to generic state
- Do not put AMM math, token balance rules, mining rules, pool registry semantics, or operator quorum logic in generic state
- Do not use `required_application_ids` as a mutable upgrade registry
- Use `required_application_ids` only when creating a new business application that depends on an existing state application
- Do not trust caller-provided operator fields as authorization
- Business upgrade handlers must validate message origin and runtime-authenticated operator identity
- Generic state upgrade handlers must validate the authenticated caller application id
- Avoid a direct recovery backdoor in generic state unless a separate task explicitly accepts that governance tradeoff

## Open Questions

- Exact generic state operation ABI
- Whether compare-and-set is required for current workflows
- Whether generic state should expose raw debug queries
- How business services read generic state bytes when service runtime cannot directly query another application service
- Exact chain permission update flow for newly created upgraded business applications
- Registry ownership for routing old business application ids to new business application ids
