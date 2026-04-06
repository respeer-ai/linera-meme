# K-line Startup Baseline Report

## Purpose

This document records the measured startup baseline for K-line loading before Phase 2 parallelization work begins.

Use it together with:

- `documents/KLINE_STARTUP_OPTIMIZATION_PLAN.md`
- `window.__klineStartupBaseline.summaries()`
- `window.__klineStartupBaseline.clear()`
- `window.__klineStartupBaseline.captureLatestSample('warm' | 'cold', note?)`
- `window.__klineStartupBaseline.samples()`
- `window.__klineStartupBaseline.clearSamples()`
- `window.__klineStartupBaseline.exportMarkdownRows()`
- `window.__klineStartupCache.clearKlineCache()`

## Measurement Rules

- capture warm-cache and cold-cache startup separately,
- capture at least `1min`, `5min`, and `10min`,
- use the same token pair for warm/cold comparison,
- record the summary from the latest completed request after each refresh,
- do not mix partially loaded or stale runs from earlier refreshes,
- if websocket updates interfere with the reading, note that explicitly.

## Warm Cache SOP

1. Open the target token pair and switch to the target interval.
2. Wait until the chart has visibly loaded once and the current interval has been written into IndexedDB.
3. Open browser devtools console.
4. Run:

```js
window.__klineStartupBaseline.clear()
```

5. Refresh the page directly without clearing IndexedDB.
6. After the chart startup completes, run:

```js
window.__klineStartupBaseline.summaries()
```

7. Take the latest completed summary for the current interval and record it in the result table.
8. Or store it immediately with:

```js
window.__klineStartupBaseline.captureLatestSample('warm')
```

Warm-cache definition:

- preserve IndexedDB K-line cache,
- allow in-memory state to reset through a normal page refresh,
- measure the real refresh startup path that should hit `LOAD_POINTS` from local cache first.

## Cold Cache SOP

1. Open browser devtools console on the target page.
2. Run:

```js
window.__klineStartupBaseline.clear()
await window.__klineStartupCache.clearKlineCache()
```

3. Refresh the page.
4. After the chart startup completes, run:

```js
window.__klineStartupBaseline.summaries()
```

5. Take the latest completed summary for the current interval and record it in the result table.
6. Or store it immediately with:

```js
window.__klineStartupBaseline.captureLatestSample('cold')
```

## Quick Export

After collecting samples, export Markdown rows with:

```js
window.__klineStartupBaseline.exportMarkdownRows()
```

This output can be pasted directly into the `Results` table after replacing the placeholder rows.

Cold-cache definition:

- IndexedDB K-line cache is cleared before refresh,
- startup is measured from an empty local K-line cache state,
- network and first-render timings should be interpreted against an empty-cache path.

## Environment

| Field | Value |
| --- | --- |
| Commit | `TBD` |
| Browser | `TBD` |
| Frontend URL | `TBD` |
| Backend URL | `TBD` |
| Token Pair | `TBD` |
| Measurement Date | `TBD` |

## Results

| Interval | Cache Mode | cacheLoadMs | networkFetchMs | mergeMs | firstRenderMs | finalPointCount | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `1min` | warm | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `1min` | cold | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `5min` | warm | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `5min` | cold | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `10min` | warm | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |
| `10min` | cold | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` | `TBD` |

## Raw Run Snapshots

Paste representative `window.__klineStartupBaseline.summaries()` output here after each measured refresh.

```json
[]
```

## Initial Observations

- `TBD`

## Decision Notes

- `TBD`
