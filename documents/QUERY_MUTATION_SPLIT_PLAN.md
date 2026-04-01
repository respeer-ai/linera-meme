# Shared Query Service Deployment Plan

## Goal

This document defines the deployment structure for separating query traffic from mutation traffic in MicroMeme.

The primary objective is:

- isolate long-running mutations from public read traffic,
- reduce `linera client` lock contention,
- keep query latency stable under write pressure,
- and centralize all read traffic into one shared query service that can later scale horizontally.

## Problem Statement

Today, product-facing services such as `blob-gateway`, `swap`, and `proxy` use the same backend pool for both GraphQL queries and GraphQL mutations.

Current pattern:

- one product service deployment,
- one product service ingress,
- one product service wallet pool,
- one product service `client.db`,
- both query and mutation traffic hitting the same service pods.

This means long-running mutations can block or degrade query responsiveness.

## Final Direction

The target architecture is:

- one shared `query-service`,
- one mutation service per product,
- all product chains synced into the shared `query-service`,
- all product read traffic routed to the shared `query-service`,
- all product write traffic routed to the corresponding mutation service.

The shared `query-service` should start with:

- `1` replica,
- one wallet,
- one `client.db`,
- and the ability to sync multiple product chains into the same query node.

Later, this service can scale horizontally for load balancing after the chain onboarding model is proven stable.

## Core Rules

### Query Service Rules

- The shared `query-service` should request one default infrastructure chain for its own wallet.
- The shared `query-service` does not create product applications.
- The shared `query-service` only initializes its own wallet and syncs product chains into its local state.
- The shared `query-service` should run with `--listener-skip-process-inbox`.
- The shared `query-service` does not need to be read-only at the service capability level.
- Query and mutation separation is enforced by caller routing, not by disabling mutation APIs in the query service.

### Mutation Service Rules

- Each mutation service owns chain creation for its product.
- Each mutation service owns application creation for its product.
- Each mutation service owns all product write flows.
- Each mutation service may still answer queries, but repository code must not use it as the normal read path.

### Storage Rules

- The shared `query-service` must use its own wallet and its own `client.db`.
- Mutation services must use separate wallets and separate `client.db` files.
- Query and mutation services must never share the same PVC for Linera client state.

## Shared Query Service Lifecycle

The shared `query-service` has two responsibilities:

1. initialize its own query wallet,
2. keep a queryable local view of all product chains that have been onboarded.

Recommended behavior:

1. initialize wallet and request one default chain once,
2. keep the service running continuously,
3. sync new product chains into that wallet during product onboarding,
4. rely on normal block synchronization afterward.

Important clarification:

- the query service should not process inbox automatically,
- but it can still sync and track new blocks after the chain has been introduced.

## Product Chain Onboarding Model

Every product should follow the same onboarding flow into the shared `query-service`.

### Standard Onboarding Steps

1. the product mutation service initializes its own wallet,
2. the product mutation service requests or opens its product chain,
3. the product mutation service creates the product application if needed,
4. the product mutation service writes the chain ID and application ID into `shared-app-data`,
5. the shared `query-service` waits for that metadata,
6. the shared `query-service` syncs the product chain into its local wallet,
7. the chain becomes available for query routing through the shared `query-service`.

### Standard Metadata Required

Each product should publish at least:

- `<PRODUCT>_MULTI_OWNER_CHAIN_ID`
- `<PRODUCT>_APPLICATION_ID`

Examples:

- `BLOB_GATEWAY_MULTI_OWNER_CHAIN_ID`
- `BLOB_GATEWAY_APPLICATION_ID`
- `SWAP_MULTI_OWNER_CHAIN_ID`
- `SWAP_APPLICATION_ID`
- `PROXY_MULTI_OWNER_CHAIN_ID`
- `PROXY_APPLICATION_ID`

## Query Service Chain Registry

To keep the deployment structure clear, the shared `query-service` should be documented as a chain registry plus query gateway.

Its internal onboarding list should eventually include:

- `blob-gateway`
- `swap`
- `proxy`
- potentially `ams` later if needed

This means the deployment structure should be thought of as:

- one query service,
- many imported product chains,
- one public query ingress surface per product path,
- but all of them landing on the same backend service.

## Public Routing Shape

Public paths should stay under the current product prefixes.

### Blob Gateway

- query: `/api/blobs/query`
- mutation: `/api/blobs/mutation`
- compatibility: `/api/blobs`

### Swap

- query: `/api/swap/query`
- mutation: `/api/swap/mutation`
- compatibility: `/api/swap`

### Proxy

- query: `/api/proxy/query`
- mutation: `/api/proxy/mutation`
- compatibility: `/api/proxy`

## Compatibility Path Rule

Compatibility paths should temporarily point to mutation services.

Examples:

- `/api/blobs` -> `blob-gateway-service`
- `/api/swap` -> `swap-service`
- `/api/proxy` -> `proxy-service`

Reason:

- mutation services already support both query and mutation semantics,
- compatibility traffic can continue to work during migration,
- but repository code must stop depending on compatibility paths.

Repository rule:

- code in this repository must never call `/api/blobs`, `/api/swap`, or `/api/proxy` as the normal product API,
- code must explicitly call either `/query` or `/mutation`.

## Ingress Structure

Ingress routing should follow this pattern:

### Blob Gateway

- `/api/blobs/query` -> `query-service`
- `/api/blobs/mutation` -> `blob-gateway-service`
- `/api/blobs` -> `blob-gateway-service`

### Swap

- `/api/swap/query` -> `query-service`
- `/api/swap/mutation` -> `swap-service`
- `/api/swap` -> `swap-service`

### Proxy

- `/api/proxy/query` -> `query-service`
- `/api/proxy/mutation` -> `proxy-service`
- `/api/proxy` -> `proxy-service`

Prefix stripping should still make the backend receive `/`.

## Query Service Deployment Structure

The shared `query-service` should be treated as an infrastructure component, not as a product service.

Recommended deployment components:

- `k8s/query/02-deployment.yaml`
- `k8s/query/03-ingress.yaml` if it also has its own direct public route

For the current product split, it is acceptable for product ingresses to forward query traffic to the shared `query-service` directly without exposing a separate standalone query hostname.

Recommended runtime shape:

- one Deployment,
- one Service,
- one PVC,
- one wallet,
- one `client.db`,
- command based on the Linera RPC-style entrypoint with `--listener-skip-process-inbox`.

## Blob Gateway Phase 1

`blob-gateway` remains the first migration target.

### Blob Gateway Mutation Service Responsibilities

- initialize blob mutation wallets,
- request or open blob chain,
- create blob application,
- publish blob chain metadata into `shared-app-data`.

### Blob Gateway Query Onboarding Responsibilities

- wait for `BLOB_GATEWAY_MULTI_OWNER_CHAIN_ID`,
- sync blob chain into the shared `query-service`,
- route blob reads through `/api/blobs/query`.

### Blob Gateway Validation Goals

- query traffic keeps responding while blob mutations are running,
- `query-service` and blob mutation service do not share the same PVC,
- blob data becomes queryable through the shared `query-service`,
- compatibility path `/api/blobs` still works through the mutation service,
- repository code can stop calling the compatibility path.

## Next Products After Blob Gateway

After `blob-gateway` is validated, the same onboarding pattern should be repeated for `swap` and then `proxy`.

### Swap Onboarding

The shared `query-service` should later sync:

- `SWAP_MULTI_OWNER_CHAIN_ID`
- and any other swap chains that must be queryable through the shared query backend.

### Proxy Onboarding

The shared `query-service` should later sync:

- `PROXY_MULTI_OWNER_CHAIN_ID`
- and any proxy-related chains required by the frontend and internal services.

## Caller Configuration Model

All callers must be upgraded to distinguish read endpoints from write endpoints.

Recommended config model:

- `BLOB_GATEWAY_QUERY_HOST`
- `BLOB_GATEWAY_MUTATION_HOST`
- `SWAP_QUERY_HOST`
- `SWAP_MUTATION_HOST`
- `PROXY_QUERY_HOST`
- `PROXY_MUTATION_HOST`

This is preferable to continuing with a single mixed `*_HOST`.

## Frontend Changes

Frontend GraphQL and HTTP clients must route by intent:

- all blob reads should go to `/api/blobs/query`,
- all swap reads should go to `/api/swap/query`,
- all proxy reads should go to `/api/proxy/query`,
- all writes should explicitly go to the mutation path.

Blob-specific note:

- current blob-facing code uses `/api/blobs`,
- this must be migrated to explicit query or mutation paths.

## Python and Service Changes

Services under `service/` must also distinguish read and write endpoints.

Typical direction:

- balances, pool reads, latest transactions, creator chain lookups, mining status -> query path,
- swaps, claims, funding actions, registration, mine, redeem, and other state-changing actions -> mutation path.

## Rollout Order

Recommended rollout order:

1. introduce the shared deployment structure for `query-service`,
2. keep `blob-gateway` on `blob-gateway-service` as the mutation-side service and add explicit query routing,
3. onboard blob chain into the shared `query-service`,
4. migrate blob callers to explicit query and mutation paths,
5. validate in the real environment,
6. onboard `swap` chains into the shared `query-service`,
7. migrate swap callers,
8. onboard `proxy` chains into the shared `query-service`,
9. migrate proxy callers.

## What This Phase Must Prove

This phase only needs to prove:

- split backends reduce lock contention,
- one shared `query-service` can safely hold multiple imported product chains,
- product mutation services can onboard their chains into the shared query backend,
- and callers can be migrated away from compatibility paths without breaking product behavior.
