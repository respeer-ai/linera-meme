# Linera Gas Probe Skill

Type: Skill
Audience: Coding assistants
Authority: High

## Purpose

Validate Conway gas cost for BCS serialization and `call_application` with disposable probe contracts and an isolated wallet.

## Trigger

Load this skill when the user writes `@skill:linera-gas-probe`, names `linera-gas-probe`, asks to validate Linera gas, asks about BCS gas cost, or asks about `call_application` gas cost.

## Rules

- Use Conway or the user-specified real network endpoint for gas validation.
- Do not use `linera net up` for gas conclusions. Local networks do not provide representative gas.
- Do not use cluster wallets or product wallets.
- Use an isolated disposable wallet, keystore, and storage path, normally under `/tmp`.
- Keep probe contracts out of product code paths.
- Copy the reusable template from `agents/skills/linera-gas-probe/assets/probe-template/` into a temporary work directory before editing or building.
- Measure with GraphQL `estimateGas` using the same pattern as `webui-v2/src/wallet/checko.ts` and `webui-v2/src/graphql/service.ts`.
- Always include a `noop` baseline and report `delta = case - noop`.
- For repeated operations, report `per_iter = delta / iterations`.
- For BCS decode probes, decode into the real target type for that payload kind. Do not substitute `Vec<u8>` unless the payload kind itself is bytes.
- Stop any local Linera GraphQL service started for the isolated wallet before finishing.
- Remove temporary probe code after copying any durable template changes back into this skill.

## Flow

1. Copy `agents/skills/linera-gas-probe/assets/probe-template/` to a temporary directory such as `/tmp/linera-gas-probe-<timestamp>` or repo-local `.tmp-gas-probe/`.
2. Build the probe contracts:
   - `cargo build --release --target wasm32-unknown-unknown`
   - `cargo build --release -p gas-probe-opgen`
3. Create an isolated wallet environment with explicit paths:
   - wallet: `/tmp/gas-probe-conway/wallet.json`
   - keystore: `/tmp/gas-probe-conway/keystore.json`
   - storage: `rocksdb:/tmp/gas-probe-conway/client.db`
4. Connect the isolated wallet to Conway and fund a new chain through the Conway faucet.
5. Publish the callee and caller modules from the temporary build output.
6. Create a callee app and caller app from those modules.
7. Start a local GraphQL service for the isolated wallet only:
   - `linera --wallet <wallet> --keystore <keystore> --storage <storage> service --listener-skip-process-inbox --port <port>`
8. Run `scripts/estimate-gas.mjs` with explicit environment variables:
   - `GAS_PROBE_RPC_URL=http://localhost:<port>`
   - `GAS_PROBE_CHAIN_ID=<isolated-chain>`
   - `GAS_PROBE_CALLER_APP_ID=<caller-app>`
   - `GAS_PROBE_CALLEE_APP_ID=<callee-app>`
   - `GAS_PROBE_OPGEN=<temp>/target/release/gas-probe-opgen`
9. Capture the table and JSON output.
10. Summarize the results by category:
   - BCS encode and decode for structured payloads
   - BCS encode and decode for byte payload sizes
   - `call_application` noop fixed cost
   - `call_application` echo payload size slope
   - `call_application` plus callee decode
11. Stop the local GraphQL service.
12. Delete temporary probe directories unless the user asks to keep them.

## Measurement Matrix

- Baseline: `noop`
- BCS payload kinds: `amount`, `account`, `account-amount`, `pool-like-small`, `bytes32`, `bytes128`, `bytes512`, `bytes2048`
- BCS cases: encode x100 and decode x100 only; do not include encode+decode mixed cases
- `call_application` cases: noop x1/x10/x100
- Echo sizes: 0, 32, 128, 512, 2048 bytes with x1/x10
- `call_application` decode cases: `amount`, `account-amount`, `pool-like-small`, `bytes512`, `bytes2048` with x1/x10


## Iteration Suffixes

- `x1`, `x10`, and `x100` are loop counts inside one submitted operation.
- They are not separate transactions and not separate blocks.
- Use higher counts to amortize fixed operation overhead.
- Report `per_iter = (case_gas - noop_gas) / iterations` for repeated cases.

## Result Format

Report:

- Network and date
- Wallet isolation paths, without private key material
- Chain id, module ids, app ids
- Baseline gas
- Key `delta` and `per_iter` rows
- Any measurement caveat, especially whether the probe code changed from the stored template
- Cleanup status

## Current Reference Result

Conway measurement on 2026-06-23 with isolated wallet `/tmp/gas-probe-conway` produced these reference observations. BCS mixed encode+decode rows are intentionally omitted from the current matrix:

- `noop`: `0.000000000000001452`
- `call_application_noop_x100` delta per iteration: `0.00000000000000225`
- `call_application_echo_512_x10` delta per iteration: `0.000000000000104337`
- `call_application_echo_2048_x10` delta per iteration: `0.000000000000390799`
- `call_application_decode_pool-like-small_x10` delta per iteration: `0.000000000000044164`
- `call_application_decode_bytes2048_x10` delta per iteration: `0.000000000000326604`

Treat these as a reference snapshot, not a permanent protocol constant. Rerun the probe before making a design decision that depends on exact gas values.
