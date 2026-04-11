# Service Routing Semantics

Type: Primitive
Audience: Coding assistants
Authority: High

## Purpose

Canonical query/mutation routing and shared-query-service rules.

## Facts

- Affected Modules:
  - `docker/`
  - `k8s/`
  - `service/kline/`
  - `webui-v2/`
- Read Before:
  - modifying API call sites
  - changing ingress or local deployment wiring
  - debugging query-service behavior

## Rules

- Read traffic should go to explicit `/query` paths
- Write traffic should go to product mutation services
- Compatibility paths may still exist but repository code should not use them as the normal product API
- Shared query service is an infrastructure component, not a product owner
- Query service has its own wallet and its own client database
- Mutation services must use separate wallets and separate client databases
- Query and mutation services must never share the same wallet or PVC-equivalent state
- `/api/blobs/query` -> query service
- `/api/blobs/mutation` and `/api/blobs` -> blob mutation service
- `/api/swap/query` -> query service
- `/api/swap/mutation` and `/api/swap` -> swap mutation service
- `/api/proxy/query` -> query service
- `/api/proxy/mutation` and `/api/proxy` -> proxy mutation service

## Implications

- Local compose must mirror this split
- Keep business hosts unchanged in service config
- Prefer local infra rewiring over changing service-level host configuration
