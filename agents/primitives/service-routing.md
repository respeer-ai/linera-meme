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
- Do not pass deployment-environment booleans such as `running_in_k8s` or `in_k8s` into core service logic, public APIs, read models, or query/runtime assembly
- Service internals should not infer routing from environment flags
- Passing a resolved endpoint or complete base URL inward is an acceptable intermediate cleanup step, but not the preferred end-state
- Preferred end-state: outer composition builds configured transport/client objects, and inner services depend on those client capabilities instead of raw URL strings
- Transport adapters may build requests from an already resolved endpoint, but endpoint selection itself belongs to deployment/config composition, not business/runtime logic
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
- If a caller already knows the correct target URL, passing that full URL downward is preferable to exposing environment-sensitive routing knobs, but it should be treated as an intermediate state before transport/client injection
