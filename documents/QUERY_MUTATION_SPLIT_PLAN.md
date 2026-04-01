# Query and Mutation Split Plan

## Goal

This document defines the first-stage plan for separating query traffic from mutation traffic in MicroMeme's Linera-facing services.

The immediate objective is:

- isolate long-running mutations from public read traffic,
- reduce `linera client` lock contention,
- keep query latency stable under write pressure,
- and validate the pattern first on `blob-gateway` before applying it to other services.

## Problem Statement

Today, services such as `swap`, `proxy`, and `blob-gateway` run a single Linera service process per pod and expose one public GraphQL endpoint for both reads and writes.

Current pattern:

- one `StatefulSet`,
- one `Service`,
- one public `Ingress`,
- one local `wallet.json` and `client.db`,
- both GraphQL queries and GraphQL mutations hit the same backend pool.

This means long-running mutations can hold the Linera client and degrade query responsiveness for all users and internal services.

## Core Design Principle

Path-based routing is only the public API shape.

It is not the actual isolation boundary.

Real isolation requires:

- a dedicated shared query backend pool,
- a dedicated mutation backend per product service,
- separate wallet directories,
- separate `client.db` files,
- and no shared PVC between query and mutation pods.

If `/query` and `/mutation` still point to the same pods or the same `client.db`, the lock problem remains.

## Public API Shape

The external API should keep the current product prefixes and add query or mutation after the product path.

Recommended public paths:

- `swap` query: `/api/swap/query`
- `swap` mutation: `/api/swap/mutation`
- `proxy` query: `/api/proxy/query`
- `proxy` mutation: `/api/proxy/mutation`
- `blob-gateway` query: `/api/blob-gateway/query`
- `blob-gateway` mutation: `/api/blob-gateway/mutation`

Compatibility paths:

- `/api/swap`
- `/api/proxy`
- `/api/blob-gateway`

Compatibility paths should temporarily point to mutation backends.

Reason:

- mutation backends already support both query and mutation semantics,
- compatibility traffic can continue to work during migration,
- but repository code must stop depending on compatibility paths and must explicitly choose `/query` or `/mutation`.

## Service Topology

The target topology should be:

- one shared query service for all products,
- one mutation service per product.

Examples:

- `query-service`
- `blob-gateway-mutation-service`
- `swap-mutation-service`
- `proxy-mutation-service`

Recommended backend ownership:

- each mutation service owns chain creation, application creation, and all write flows for its product,
- the shared query service owns read traffic only and maintains a local queryable view of all imported product chains.

Initial deployment target for the shared query service:

- one replica only.

Later evolution:

- horizontal scale-out for load balancing after the import and sync model is proven stable.

## Chain Initialization Model

The initialization rule is:

- request or open chains only in the mutation service,
- import or sync those chains into the shared query service.

The shared query service must not create product chains.

Recommended init flow:

1. mutation service initializes its wallet,
2. mutation service requests or opens the chain,
3. mutation service creates the application if needed,
4. mutation service writes chain and application metadata into `shared-app-data`,
5. the shared query service initializes its own wallet,
6. the shared query service imports or syncs the chain created by the mutation service,
7. the shared query service updates its local queryable state,
8. the shared query service starts or keeps running its own `linera service`.

Important rules:

- query and mutation wallets must be separate,
- query and mutation `client.db` must be separate,
- the shared query service must never reuse mutation `wallet.json` or `keystore.json`,
- shared state should only pass chain IDs, application IDs, and other metadata.

## `sync` vs `import-chain`

Preferred order:

1. use `sync` if it reliably makes the chain queryable in the query service,
2. fall back to `import-chain` if `sync` is insufficient.

The decision should be based on real validation in the target environment.

## Ingress Routing Rules

Each public query path should be routed to the shared query service, and each public mutation path should be routed to the corresponding mutation service. Product prefixes should be stripped before forwarding.

Example for `blob-gateway`:

- `/api/blob-gateway/query` -> `query-service`
- `/api/blob-gateway/mutation` -> `blob-gateway-mutation-service`
- `/api/blob-gateway` -> `blob-gateway-mutation-service`

The backend should still receive the request at `/`.

This keeps Linera service behavior unchanged while allowing path-based traffic separation at the edge.

## Blob Gateway Pilot

`blob-gateway` should be used as the first pilot service.

Reason:

- it uses the same single-pool deployment pattern as `swap` and `proxy`,
- it lets us validate the deployment pattern before touching trading-critical services,
- and failure impact is lower than changing the trading path first.

### Current `blob-gateway` State

Today `blob-gateway` is deployed as:

- one `StatefulSet`,
- one `Service`,
- one public `Ingress`,
- one wallet per pod,
- one public GraphQL surface.

Relevant manifests:

- [k8s/blob-gateway/02-deployment.yaml](/home/kk/linera-project/linera-meme/k8s/blob-gateway/02-deployment.yaml)
- [k8s/blob-gateway/03-ingress.yaml](/home/kk/linera-project/linera-meme/k8s/blob-gateway/03-ingress.yaml)

### Blob Gateway Pilot Target

Create:

- `blob-gateway-mutation-service`
- `query-service`

Public routes:

- `/api/blob-gateway/query`
- `/api/blob-gateway/mutation`
- `/api/blob-gateway`

Route ownership:

- `/api/blob-gateway/query` -> shared query backend
- `/api/blob-gateway/mutation` -> mutation backend
- `/api/blob-gateway` -> mutation backend during migration

### Blob Gateway Pilot Steps

1. Split the existing `blob-gateway` deployment into a mutation deployment and a shared query deployment.
2. Keep all chain creation and application creation logic only in the `blob-gateway` mutation deployment.
3. Make the shared query deployment wait for mutation-side chain and application metadata in `shared-app-data`.
4. Initialize a separate query wallet and separate query `client.db`.
5. Import or sync the mutation-created `blob-gateway` chain into the shared query deployment.
6. Expose the shared query Service, the `blob-gateway` mutation Service, and one updated Ingress with path-based routing.
7. Validate that long mutations no longer degrade query latency.

### Blob Gateway Validation Checklist

- query requests stay responsive while mutation requests are running,
- the shared query pod and mutation pods do not share the same PVC,
- the shared query backend can serve current application state after import or sync,
- compatibility path `/api/blob-gateway` still works during migration through the mutation backend,
- internal callers can explicitly choose query or mutation paths.

## Client and Service Changes Required After the Pilot

Infrastructure changes alone are not enough.

All callers must be upgraded to distinguish read endpoints from write endpoints.

Repository rule:

- code in this repository must not call compatibility paths such as `/api/blob-gateway`, `/api/swap`, or `/api/proxy`,
- code must explicitly call either the query path or the mutation path.

Recommended config model:

- `BLOB_GATEWAY_QUERY_HOST`
- `BLOB_GATEWAY_MUTATION_HOST`
- `SWAP_QUERY_HOST`
- `SWAP_MUTATION_HOST`
- `PROXY_QUERY_HOST`
- `PROXY_MUTATION_HOST`

This is preferable to continuing with a single `*_HOST` value for mixed traffic.

## Frontend Changes

Frontend GraphQL clients must route by operation type:

- GraphQL `query` -> query endpoint,
- GraphQL `mutation` -> mutation endpoint.

For the web UI, this should be implemented in the shared GraphQL client layer rather than scattered across pages or stores.

## Python Service Changes

Services under `service/kline` and related automation clients must also be split by operation type.

Typical examples:

- state reads, balances, creator chain lookups, pool reads, and transaction reads -> query endpoint,
- swaps, claims, funding actions, and other state-changing operations -> mutation endpoint.

## Miner Changes

`miner` must also distinguish between reads and writes.

Typical direction:

- mining info, balances, meme metadata, and registration status -> query endpoint,
- `mine`, `redeem`, `registerMiner`, and other write operations -> mutation endpoint.

## Rollout Order

The rollout should remain incremental.

Recommended order:

1. document and validate the pattern on `blob-gateway`,
2. introduce the shared `query-service` with one replica,
3. update internal client configuration model to support separate query and mutation endpoints,
4. migrate `blob-gateway`,
5. validate behavior in the real environment,
6. import `swap` chains into the shared query service and migrate `swap` writes to its mutation service,
7. import `proxy` chains into the shared query service and migrate `proxy` writes to its mutation service,
8. then update remaining services that still assume a single mixed endpoint.

## Non-Goals for the Pilot

The `blob-gateway` pilot should not try to solve every cross-service routing issue at once.

Specifically out of scope for the first step:

- full migration of `swap`,
- full migration of `proxy`,
- full frontend rollout,
- protocol changes inside Linera,
- or broader product-level traffic redesign.

The pilot only needs to prove that:

- split backends reduce lock contention,
- path-based external routing is workable,
- a single shared query backend can safely serve imported chains from multiple products,
- and mutation-created chains can be safely consumed by that shared query backend.
