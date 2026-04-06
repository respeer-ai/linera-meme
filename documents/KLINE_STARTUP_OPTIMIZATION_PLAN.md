# K-line Startup Optimization Plan

## Purpose

This document defines the optimization strategy for making the K-line chart open near-instantly.

Target outcome:

- cached K-line opens in under `300ms`,
- uncached K-line shows a usable first screen in under `1s`,
- recent candles are visible before historical backfill finishes,
- indicator computation and background synchronization do not block first paint.

## Time Convention

All estimates use AI work time.

- `0.25d` = a short focused AI work block.
- `0.5d` = half a focused AI work day.
- `1d` = one focused AI work day.
- `3d` = three focused AI work days.

## Delivery Constraint

TDD and complete testing are hard constraints for this execution track.

Required rule:

- every functional change must start from a failing test or a missing-test case definition,
- implementation is not complete until the related test suite is added or updated and passing,
- no task may be marked `DONE` with manual verification alone,
- if a change spans frontend, worker, IndexedDB, API, or backend query paths, coverage must include the affected layers, not only the leaf function,
- regression coverage is mandatory for every bug fix.

Minimum test expectation by change type:

- frontend state or orchestration change: unit tests plus integration tests for startup flow and merge behavior,
- chart rendering-path change: incremental-update regression tests and first-paint behavior verification,
- worker or IndexedDB change: worker-path tests and cache/network merge tests,
- backend query or storage change: unit tests, query-path integration tests, and performance-oriented verification on representative windows,
- websocket scope change: subscription-behavior tests and irrelevant-update suppression tests.

## Current Startup Flow

Current webui-v2 startup path:

1. `PriceChartView` clears in-memory points and starts `LOAD_POINTS`.
2. Worker reads IndexedDB for the selected `token0/token1/interval`.
3. Loaded points are merged and rendered.
4. If data is incomplete, frontend continues with `FETCH_POINTS`.
5. Chart redraw recalculates all series and indicators from the full point set.

Primary files involved:

- `webui-v2/src/components/kline/PriceChartView.vue`
- `webui-v2/src/worker/kline/runner.ts`
- `webui-v2/src/bridge/db/kline.ts`
- `webui-v2/src/components/kline/chart/ChartView.vue`
- `service/kline/src/db.py`
- `service/kline/src/subscription.py`

## Measured Reality

Measured live backend response times for a recent active market on `2026-04-06`:

- `1min`, 1-hour window: about `0.62s`
- `5min`, 5-hour window: about `1.35s`
- `10min`, 10-hour window: about `4.13s`

This means frontend optimization alone is not sufficient. The backend points path is already slow enough to block perceived startup quality.

## Current Bottlenecks

### 1. Wrong Forward Refill Direction

In `PriceChartView`, when the chart already has cached data but needs newer candles, the no-new-points branch can continue fetching from the wrong side of the range.

Observed consequence:

- startup can spend time crawling from historical points instead of filling the latest visible edge,
- users see delayed right-edge completion even when local cache exists.

Impact:

- high

### 2. Startup Is Serialized Instead of Parallel

The chart currently waits for IndexedDB `LOAD_POINTS` before it meaningfully advances to network fetch of the latest window.

Observed consequence:

- cold start pays local cache lookup cost and network cost sequentially,
- empty cache startup is slower than necessary,
- warm cache still delays latest-candle correctness.

Impact:

- high

### 3. Full Redraw on Every Point Update

`ChartView` rebuilds candle data, volume data, MA, EMA, and Bollinger data and calls full `setData()` on all series whenever `props.data` changes.

Observed consequence:

- one appended candle can trigger a full chart recomputation,
- startup render cost scales with point count,
- indicator-heavy views cost much more than needed.

Impact:

- high

### 4. Points Endpoint Aggregates from Raw Transactions Every Time

`service/kline/src/db.py` loads raw `transactions` rows into pandas and resamples on demand for every `/points` request.

Observed consequence:

- request latency grows with raw transaction volume,
- backend work is repeated for the same interval windows,
- Python memory and pandas overhead are on the critical path.

Impact:

- very high

### 5. Missing Query Index for Points Access Pattern

The current `transactions` table has primary key `(pool_id, transaction_id, token_reversed)` but the K-line query pattern is `(pool_id, token_reversed, created_at BETWEEN ...)`.

Observed consequence:

- the database cannot serve the K-line path efficiently,
- larger markets will degrade disproportionately.

Impact:

- very high

### 6. WebSocket Pushes Too Much Data

The backend pushes all pools and all intervals every 10 seconds.

Observed consequence:

- frontend receives and stores large amounts of irrelevant points,
- IndexedDB and main-thread work continue even when a user only looks at one pair and one interval.

Impact:

- medium

### 7. Indicator Computation Blocks First Useful Paint

Volume and technical indicators are recomputed together with the main chart data.

Observed consequence:

- chart readiness waits for non-essential work,
- startup latency grows with enabled indicator count.

Impact:

- medium

## Optimization Strategy

### Phase 1: Fix Current Fetch Direction and Add Instrumentation

Estimated effort: `0.5d`

Deliverables:

- correct right-edge refill behavior,
- startup timing instrumentation for `LOAD_POINTS`, `FETCH_POINTS`, merge, and first render,
- logs or metrics that separate cache time, network time, and render time.

Acceptance criteria:

- startup no longer backfills from the wrong side,
- timing breakdown is visible in development and test environments.

### Phase 2: Make Startup Parallel

Estimated effort: `0.75d - 1.25d`

Deliverables:

- start IndexedDB load and latest-window network fetch in parallel,
- render whichever result arrives first,
- merge latest network data over cache data without waiting for full historical completion,
- define a first-screen fetch window per interval.

Acceptance criteria:

- empty cache first paint is faster than current serialized flow,
- warm cache shows first screen immediately while newer candles continue to hydrate.

### Phase 3: Split First Paint from Historical Backfill

Estimated effort: `0.75d - 1.5d`

Deliverables:

- first-screen mode that requests only the visible window,
- deferred historical backfill after first paint,
- explicit background history status instead of blocking chart readiness.

Acceptance criteria:

- chart becomes visible before full history arrives,
- users can inspect the current market without waiting for older candles.

### Phase 4: Move Chart Updates to Incremental Rendering

Estimated effort: `1.5d - 2.5d`

Deliverables:

- replace full-series redraws with append/update logic where possible,
- remove deep full-data watcher from the main hot path,
- update only changed candles and volume bars,
- preserve chart state during incremental refresh.

Acceptance criteria:

- adding a small number of candles does not trigger full series rebuild,
- startup and live updates remain smooth with several hundred points.

### Phase 5: Defer Non-Essential Indicator Work

Estimated effort: `0.75d - 1.25d`

Deliverables:

- render candle and volume first,
- compute MA/EMA/BOLL after first useful paint,
- optionally use idle-time or deferred scheduling for heavier indicators.

Acceptance criteria:

- first useful paint no longer depends on all indicators being ready,
- indicator-heavy configurations remain responsive.

### Phase 6: Add Backend Indexes and Remove Obvious Query Waste

Estimated effort: `0.75d - 1.5d`

Deliverables:

- add a query-serving index for K-line range access,
- normalize time-unit handling,
- reduce redundant full-range scans where possible.

Acceptance criteria:

- live `/points` latency materially improves without changing API semantics,
- 5-minute and 10-minute windows no longer take multiple seconds on active markets.

### Phase 7: Replace On-Demand Pandas Aggregation with Pre-Aggregated Candles

Estimated effort: `2.5d - 4d`

Deliverables:

- candle storage model keyed by `pool_id`, `token_reversed`, `interval`, and bucket start,
- incremental candle maintenance on new transaction ingest,
- `/points` reads from candle storage instead of rebuilding from raw transactions.

Acceptance criteria:

- points requests become mostly storage reads instead of resample jobs,
- backend latency falls to a level consistent with near-instant frontend startup.

### Phase 8: Reduce WebSocket Broadcast Scope

Estimated effort: `1d - 2d`

Deliverables:

- pair-aware and interval-aware subscription model,
- push only relevant updates to connected clients,
- send incremental candle updates instead of broad snapshots where feasible.

Acceptance criteria:

- frontend background churn is reduced,
- IndexedDB write volume is materially lower during idle viewing.

## Recommended Execution Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7
8. Phase 8

This order is intentional:

- first remove obviously wrong fetch behavior,
- then improve perceived startup without backend redesign,
- then reduce frontend redraw cost,
- then reduce backend response latency structurally.

## Execution Task Board

This board is the execution baseline for follow-up work. Status should be updated in this document as tasks move.

Status convention:

- `TODO`: defined but not ready to start,
- `READY`: dependencies are clear and the task can start,
- `IN PROGRESS`: actively being executed,
- `BLOCKED`: cannot proceed until a dependency is resolved,
- `DONE`: implemented and verified against the acceptance criteria.

Execution rule:

- phases remain the sequencing frame,
- task rows are the actual execution unit,
- no Phase 4+ work should start until Phase 1-3 instrumentation confirms the startup path being optimized,
- each task should land with measurable evidence, not only code changes,
- each task must define its test delta before implementation starts,
- each task reaches `DONE` only after all related tests are green.

| ID | Phase | Task | Scope / Expected Output | Dependency | Required Test Coverage | Suggested Owner | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| KSO-01 | Phase 1 | Fix right-edge refill direction | Correct forward refill start/end selection in `PriceChartView`; verify latest-edge completion uses the newest missing range first | None | Add regression tests for wrong-direction refill, right-edge priority, and no duplicate range fetch behavior | Frontend | DONE |
| KSO-02 | Phase 1 | Add startup instrumentation | Add timing points for cache load, network fetch, merge, first paint, indicator completion; produce development-visible logs or metrics | KSO-01 | Add tests covering instrumentation emission for warm cache, cold cache, and partial-cache startup paths | Frontend | DONE |
| KSO-03 | Phase 1 | Establish startup baseline report | Capture before/after measurements for warm cache and cold cache on representative intervals; append result summary to this plan or a linked record | KSO-02 | Add or update verification harness/tests that assert timing fields are emitted and measurement collection remains stable | Frontend | IN PROGRESS |
| KSO-04 | Phase 2 | Parallelize cache load and latest fetch | Start IndexedDB read and latest-window fetch concurrently; first arrival can render immediately | KSO-02 | Add startup orchestration tests proving cache and network begin in parallel and first arrival can paint | Frontend | TODO |
| KSO-05 | Phase 2 | Define first-screen fetch window | Lock interval-specific visible-window policy so parallel fetch has bounded scope and stable semantics | KSO-04 | Add tests for interval-to-window mapping and request-boundary correctness | Frontend | TODO |
| KSO-06 | Phase 2 | Merge cache and network deterministically | Newer network candles overwrite cache overlap without causing startup flicker or duplicate points | KSO-04 | Add merge tests for overlap, out-of-order arrival, dedupe, and latest-candle overwrite semantics | Frontend | TODO |
| KSO-07 | Phase 3 | Split first paint from historical backfill | First screen requests only visible data; older history loads in background | KSO-05, KSO-06 | Add tests proving first paint does not wait for full history and backfill starts only after visible data is ready | Frontend | TODO |
| KSO-08 | Phase 3 | Add background history state | Surface explicit backfill/loading status so chart readiness is not tied to full-history completion | KSO-07 | Add UI/state tests for background-history indicators and readiness-state transitions | Frontend | TODO |
| KSO-09 | Phase 4 | Convert chart hot path to incremental candle updates | Replace full-series rebuild for candle and volume with append/update logic where possible | KSO-07 | Add rendering-path tests proving append/update avoids full-series reset for small deltas | Frontend | TODO |
| KSO-10 | Phase 4 | Remove deep full-data redraw trigger | Refactor watcher/update path so small point changes do not force all series recomputation | KSO-09 | Add regression tests that small point updates do not trigger full redraw pathways | Frontend | TODO |
| KSO-11 | Phase 4 | Preserve chart interaction state during incremental refresh | Keep visible range, crosshair usability, and active overlay behavior stable during append/update | KSO-09 | Add interaction regression tests for visible range, crosshair, and overlay stability during incremental refresh | Frontend | TODO |
| KSO-12 | Phase 5 | Defer indicator computation after first useful paint | Candles and volume render first; MA/EMA/BOLL compute later using deferred scheduling | KSO-09 | Add tests proving first useful paint completes before deferred indicators and indicators eventually reconcile correctly | Frontend | TODO |
| KSO-13 | Phase 5 | Measure indicator impact separately | Confirm first useful paint and indicator-ready timings are independently visible | KSO-12 | Add tests for separate timing emission and stable measurement naming for indicator phases | Frontend | TODO |
| KSO-14 | Phase 6 | Add query-serving index for points access | Add index aligned to `(pool_id, token_reversed, created_at)` access pattern and validate query plan improvement | None | Add backend tests for indexed points access behavior and query-plan or execution-path verification where practical | Backend | READY |
| KSO-15 | Phase 6 | Remove obvious backend range-scan waste | Normalize time handling and reduce unnecessary full-range processing without changing API semantics | KSO-14 | Add backend integration tests for time-range correctness, unchanged API responses, and reduced redundant scanning behavior | Backend | TODO |
| KSO-16 | Phase 6 | Re-measure live `/points` latency | Capture latency after index/query cleanup for `1min`, `5min`, and `10min` representative windows | KSO-15 | Add or update repeatable measurement harness coverage so latency collection remains reproducible | Backend | TODO |
| KSO-17 | Phase 7 | Design pre-aggregated candle storage model | Define schema keyed by pool, reverse flag, interval, and bucket start; document write/update semantics | KSO-16 | Add schema-level and aggregation-contract tests for bucket keying, interval correctness, and idempotent writes | Backend | TODO |
| KSO-18 | Phase 7 | Implement incremental candle maintenance | Update candle storage on transaction ingest rather than rebuilding on read | KSO-17 | Add ingest-path tests for candle creation, update, bucket rollover, replay/idempotency, and reverse-token handling | Backend | TODO |
| KSO-19 | Phase 7 | Switch `/points` to candle storage reads | Serve points from pre-aggregated candles and preserve current API behavior | KSO-18 | Add end-to-end query tests proving `/points` matches previous semantics while using candle storage | Backend | TODO |
| KSO-20 | Phase 8 | Narrow WebSocket subscription scope | Make subscription pair-aware and interval-aware instead of broadcasting broad updates | KSO-19 | Add subscription tests for pair filtering, interval filtering, and irrelevant-update suppression | Backend | TODO |
| KSO-21 | Phase 8 | Push incremental candle updates | Send only changed candles where feasible to reduce frontend churn and IndexedDB writes | KSO-20 | Add websocket payload tests and frontend-consumer regression tests for incremental update application | Backend | TODO |
| KSO-22 | Cross-phase | Define completion gate for "feels instant" milestone | Confirm Phase 1 + 2 + 3 + 6 satisfy warm-cache `<300ms` and usable uncached first screen `<1s` targets | KSO-03, KSO-08, KSO-16 | Add milestone verification suite covering target startup timings, readiness states, and representative backend latency thresholds | Frontend + Backend | TODO |
| KSO-23 | Cross-phase | Enforce strict financial candle semantics | Align HTTP `/points` and WebSocket candle generation to strict financial semantics: interval-boundary alignment, closed-vs-forming candle semantics, consistent volume for the same closed bucket, and explicit metadata when the latest candle is still forming | KSO-16, KSO-19, KSO-21 | Add backend and frontend regression tests covering identical closed-bucket OHLCV across HTTP and WebSocket, boundary alignment for `1min/5min/10min/1h`, and explicit handling of forming candles | Frontend + Backend | TODO |

Recommended first execution slice:

1. KSO-01
2. KSO-02
3. KSO-03
4. KSO-04
5. KSO-05
6. KSO-06
7. KSO-14
8. KSO-15
9. KSO-16

This slice creates the minimum measurement loop needed to decide whether frontend parallelization alone is enough or whether backend path work must move forward immediately.

## Baseline Capture Procedure

KSO-03 should use the built-in startup baseline recorder in development builds.

Development helpers:

- `window.__klineStartupBaseline.summaries()` returns captured startup summaries by request,
- `window.__klineStartupBaseline.clear()` clears previously captured summaries,
- `window.__klineStartupCache.clearKlineCache()` clears IndexedDB K-line cache for cold-cache measurement.

Recommended measurement flow:

1. Open the target market and target interval.
2. Run `window.__klineStartupBaseline.clear()`.
3. For warm-cache measurement, refresh directly after the chart has fully loaded once.
4. For cold-cache measurement, run `await window.__klineStartupCache.clearKlineCache()` and then refresh.
5. After each refresh, read `window.__klineStartupBaseline.summaries()` and record:
   `cacheLoadMs`, `networkFetchMs`, `mergeMs`, `firstRenderMs`, and `finalPointCount`.
6. Repeat for at least `1min`, `5min`, and `10min`.

Baseline record format:

- environment: browser, commit hash, backend target
- pair: token0/token1
- interval: `1min` / `5min` / `10min`
- cache mode: warm / cold
- cacheLoadMs
- networkFetchMs
- mergeMs
- firstRenderMs
- finalPointCount
- notes: anomalies, empty fetches, stale websocket effects, or partial-history behavior

## Fastest Path to "Feels Instant"

If the goal is the fastest visible improvement with minimal surface area, do this subset first:

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 6

Estimated effort: `2.75d - 5.75d`

Expected result:

- major reduction in first visible chart latency,
- much better warm-cache behavior,
- backend no longer dominates smaller-window startup as severely.

## Full "Near-Instant" Path

If the goal is sustainable K-line startup quality under growing market activity, complete all phases.

Estimated effort: `8.25d - 15d`

Expected result:

- cached chart can reliably feel instant,
- uncached chart can show useful data quickly,
- backend scales better with trade volume,
- background updates stop wasting frontend resources.

## Implementation Notes

### Frontend Principles

- never block first paint on full history,
- never block first paint on secondary indicators,
- avoid deep watchers on large point arrays,
- prefer append/update over full series resets,
- treat cache as optional acceleration, not as a gate,
- write failing tests before changing startup orchestration or rendering behavior,
- do not merge frontend behavior changes without unit and integration coverage.

### Backend Principles

- avoid rebuilding candles from raw trades on every read,
- align storage indexes with actual query predicates,
- keep hot-path aggregation out of Python where possible,
- precompute or incrementally maintain interval buckets,
- write failing tests before changing query, storage, or subscription semantics,
- do not merge backend behavior changes without query-path and regression coverage.

## Immediate Next Step

Start with Phase 1 and Phase 2 in one execution track:

- fix forward refill direction,
- add startup instrumentation,
- parallelize cache load and latest-window network fetch,
- render first-arrival data immediately.

This is the lowest-risk path to noticeably faster K-line startup.
