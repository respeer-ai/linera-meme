# Testing Runbook

Type: Runbook
Audience: Coding assistants
Authority: High

## Purpose

Default testing workflow and coverage expectations.

## Facts

- Inputs:
  - code change or behavior change under validation
  - target layer such as contract, service, or frontend
- Outputs:
  - passing targeted tests
  - regression coverage for changed behavior
  - explicit note if some verification could not be run
- Stop Conditions:
  - required tests added or updated and executed
  - or verification blocker identified explicitly

## Rules

- Prefer targeted tests first
- Start from a failing test or a clearly defined missing-test case when changing behavior
- A bug fix is not complete without regression coverage
- When running `cargo test`, always apply explicit memory limits to avoid host lockups
- Do not run `cargo test` without an explicit memory limit
- Treat that limit as an explicit virtual-memory cap, not as a statement about required physical RAM
- If Wasmer-heavy tests still fail with `Failed to create memory` or `os error 12`, raise the virtual-memory cap gradually and rerun; sandboxed environments may need a larger cap than an unrestricted local machine
- For heavier Rust suites, also reduce job count and test parallelism

- Cover happy path and duplicate or replay delivery edges
- Cover wrong-chain execution where relevant
- Cover async message-chain termination points, not just initiating operations
- Cover queue boundaries such as `latestTransactions`

- For `service/kline`, cover query-path behavior, aggregation semantics, and API parameter validation
- For frontend startup or chart changes, cover cache merge behavior, live update behavior, and stale overwrite prevention

## Checklist

- When running `cargo test`, set explicit memory limits before execution
- Prefer `cargo test -j 1` for heavy Rust integration suites, then raise the virtual-memory cap step by step if Wasmer module instantiation still fails
- When running heavy Rust tests, reduce parallelism and memory pressure
- Avoid host-freezing test settings
