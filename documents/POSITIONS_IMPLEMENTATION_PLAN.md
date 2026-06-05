# Positions Implementation Note

> Audience: humans
>
> This document is historical.
> It is not the task board and not the canonical implementation source.
> Live task tracking is maintained in `agents/tasks/board.yaml`; current assistant-facing constraints live under `agents/`.

## Current Status

The positions page is no longer a static prototype. `webui-v2` has a positions route and consumes backend position APIs.

`service/kline` exposes projection-backed position and position-metrics read paths. Product runtime must not reconstruct position truth from live pool GraphQL or frontend-side pool scans.

Current principles:

- Positions are product projections derived from parsed chain facts and normalized market events.
- The frontend consumes positions APIs and wallet identity; it must not invent position state.
- Virtual initial liquidity is a distinct protocol/product fact and must not be confused with normal add-liquidity positions.
- Protocol fee and trading yield display must be derived from backend/projection accounting, not frontend approximation.
- Future funding consistency work may move owed values into claim balances; positions UI must consume the resulting product API rather than reimplement accounting.

## Historical Plan Summary

The original plan proposed a backend positions API with `owner` and `status` filters, plus frontend rendering for active and closed positions. That direction has been implemented and evolved.

Historical ideas retained for context:

- `GET /positions?owner=...&status=active|closed|all`
- backend aggregation by owner and pool
- frontend rendering of active/closed position cards
- tests for only-add, partial-remove, full-remove, multiple pools, multiple users, reopen-after-close, and non-liquidity exclusion

Do not use this historical plan to override current code, task-board status, or funding/observability primitives.
