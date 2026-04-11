# Docker Local Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Purpose

Local deployment rules for `docker/compose.sh`, `docker/restart.sh`, and docker compose wiring.

## Facts

- Scope:
  - applies to `docker/`
  - applies to local compose deployment driven by `docker/compose.sh` and `docker/restart.sh`
- Affected Services:
  - query-service
  - maker-wallet
  - kline
  - maker
  - funder

## Rules

- Local compose must mirror k8s read/write separation semantics
- Keep business hosts unchanged in service config:
  - `api.${CLUSTER}.lineraswap.fun`
  - `api.${CLUSTER}.linerameme.fun`
- Do not replace business hosts in service config with internal container addresses just to make local compose work
- Local deployment needs a dedicated query service equivalent
- Local deployment needs a dedicated maker wallet service equivalent
- Query and maker wallet must use separate wallets
- Local query service must use `rpc-entrypoint.sh`
- Local query service must be initialized before dependent services start
- Local query wallet must import required multi-owner chains before serving traffic
- At minimum import:
  - `SWAP_MULTI_OWNER_CHAIN_ID`
  - `PROXY_MULTI_OWNER_CHAIN_ID`
- Local `kline-service` must read via query only
- Local `kline-service` must not depend on wallet RPC
- Local `maker-service` must read via query
- Local `maker-service` must write via maker wallet RPC
- If local DNS or proxy rewrites are used, use them to make business hosts resolve to local services
- Prefer changing local infra wiring over changing service-level host configuration
- When using compose files with relative volume paths, ensure the runtime `-f` path resolves those paths to `output/compose/...` as intended
- Keep `query-service` startup mechanism aligned with `maker-wallet` startup mechanism when they use the same relative-path pattern

## Checklist

- Query and maker wallet compose files resolve wallet mounts into `output/compose/wallet/...`
- Query service starts before dependent read traffic
- Required chains are imported before query traffic depends on them
- Wallet owner and chain metadata are read before wallet-locking services start
