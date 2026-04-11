# WebUI V2 Rules

Type: Rules
Audience: Coding assistants
Authority: High

## Purpose

Local rules for `webui-v2/` code and frontend bug fixing.

## Facts

- Scope:
  - applies to `webui-v2/`
- High-Risk Areas:
  - `src/components/kline/`
  - `src/worker/kline/`
  - `src/bridge/db/`
  - `src/stores/kline/`
  - `src/stores/positions/`
  - `src/stores/notify/`
- Frontend Role:
  - consume APIs
  - consume wallet state
  - render positions, chart, and protocol UI

## Rules

- Do not patch frontend display for issues that originate in contracts, transaction persistence, or `service/kline`
- For chart bugs, separate:
  - backend `/points` response correctness
  - local cache merge correctness
  - live update correctness
  - render-layer correctness
- For user-visible request failures, use the app notify mechanism instead of raw inline error text unless the page already defines a different explicit pattern
- Preserve existing visual language outside the target surface; do not restyle unrelated pages while implementing a focused task
- When changing `positions`, align with V2 semantics:
  - `active`
  - `closed`
  - `LMM` as liquidity share, not tradeable token
- When changing kline startup behavior, avoid timing hacks that mask root-cause ordering bugs
- When changing worker/cache logic, consider cross-device and stale-cache divergence explicitly

## Checklist

- Upstream-vs-frontend root cause separated
- Notify behavior used consistently for user-visible failures
- Targeted store/worker/component tests or build/lint validation run when applicable
- Unrelated pages not modified
