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
- Each measured case must perform exactly one operation pattern. Do not use repeated loops to amortize fixed cost unless the user explicitly asks for a separate amortization run.
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
   - direct typed local state read/write for business payloads
   - raw byte state read/write as auxiliary byte-size reference
   - local generic state BCS encode/write and read/decode
   - `call_application` generic state BCS encode/write and read/decode
11. Stop the local GraphQL service.
12. Delete temporary probe directories unless the user asks to keep them.

## Measurement Matrix

- Baseline: `noop`
- BCS payload kinds: `amount`, `account`, `account-amount`, `pool-like-small`, `bytes32`, `bytes128`, `bytes512`, `bytes2048`
- BCS cases: one encode or one decode only; do not include encode+decode mixed cases
- `call_application` cases: one noop call
- Echo sizes: 0, 32, 128, 512, 2048 bytes with one call each
- `call_application` decode cases: `amount`, `account-amount`, `pool-like-small`, `bytes512`, `bytes2048` with one call each
- Direct typed local state cases:
  - `typed_state_read_<payload>`
  - `typed_state_write_<payload>`
- Raw byte state cases: `raw_state_read_bytes<bytes>` and `raw_state_write_bytes<bytes>` for 32, 512, and 2048 bytes
- Local generic state cases:
  - `generic_state_bcs_encode_write_<payload>`
  - `generic_state_read_bcs_decode_<payload>`
- Cross-application generic state cases:
  - `call_application_generic_state_bcs_encode_write_<payload>`
  - `call_application_generic_state_read_bcs_decode_<payload>`
- Generic payload kinds: `amount`, `account-amount`, `pool-like-small`, `bytes512`, `bytes2048`
- Read cases must use seeded read keys.
- Write cases must use separate write keys so write estimates do not overwrite read baselines.
- For each payload kind, typed state read/write, BCS encode/decode, local generic state, and cross-application generic state must use the same sample payload data.

## Generic State Comparisons

Use these rows together for generic state design decisions:

- Direct typed read cost: `typed_state_read_<payload>`
- Direct typed write cost: `typed_state_write_<payload>`
- Raw byte read cost: `raw_state_read_bytes<bytes>`
- Raw byte write cost: `raw_state_write_bytes<bytes>`
- Pure encode cost: `bcs_encode_<payload>`
- Pure decode cost: `bcs_decode_<payload>`
- Local generic write cost: `generic_state_bcs_encode_write_<payload>`
- Local generic read cost: `generic_state_read_bcs_decode_<payload>`
- Cross-app generic write cost: `call_application_generic_state_bcs_encode_write_<payload>`
- Cross-app generic read cost: `call_application_generic_state_read_bcs_decode_<payload>`

Semantics:

- Direct typed state rows read or write the business payload type in the caller application state without an explicit business-level BCS conversion step.
- Raw byte state rows read or write `Vec<u8>` state without business-level BCS encode/decode; use them only as auxiliary byte-size references.
- Local generic write encodes a typed payload to bytes, then writes those bytes into state.
- Local generic read reads bytes from state, then decodes into the typed payload.
- Cross-app generic write calls the generic state application; the callee writes already encoded bytes to state.
- Cross-app generic read calls the generic state application; the callee reads bytes and decodes them.
- Use `call_application_noop` to reason about the fixed call overhead separately.

## Single-Operation Measurements

- Do not add `x1`, `x10`, or `x100` suffixes for the default matrix.
- Each row is one submitted operation containing one measured read, write, encode, decode, or `call_application` pattern.
- Report `delta = case_gas - noop_gas`; do not divide by an iteration count.
- Keep sample data identical across typed state, BCS, local generic state, and cross-application generic state for the same payload kind.

## Result Format

Report:

- Network and date
- Wallet isolation paths, without private key material
- Chain id, module ids, app ids
- Baseline gas
- Key `delta` rows
- Any measurement caveat, especially whether the probe code changed from the stored template
- Cleanup status

## Current Reference Result

Conway measurement on 2026-06-23 with isolated wallet `/tmp/gas-probe-conway-1782208134` produced these single-operation reference observations. Each row is `delta = case_gas - noop_gas`; no loop count or per-iteration averaging is used.

Environment:

- Chain: `d26d58c7e6929563c837030e546d626900cf0747c27d8ec0477f0d25c56da2b9`
- Callee app: `7741f65b6bf75c261eb03f77df994cadf146528919e42a57cfb0b866968bb990`
- Caller app: `6473c6aca51a0039c3a9d05e9785b40104a5e9c1fa7ab5d85e023875a62798ef`
- Callee module: `db40dd6c6f3fa8b3678173b2bb2478be3d6b72b9dbd0a5b5d04f08c4ee3288637f7dbc32f214d171dcd88e8aaab7c8b66806dd81fa6439ed8d66eac7e28e135600`
- Caller module: `aa45692ffce8214280f2405a840b053877b75e5299ba606971af5b8f0d5372778e8cfe9b4d5d44dd3095e7767b8ecfc1cad84b87e2a75726d3dc85c0566368a500`
- Local client: Linera v0.15.15; Conway faucet reported Linera v0.15.19 with matching WIT API hash.

Selected rows:

- `noop`: `0.000000000000019907`
- `call_application_noop`: `0.000000000000010377`
- `bcs_encode_amount`: `0.000000000000000692`
- `bcs_decode_amount`: `0.000000000000001841`
- `bcs_encode_pool-like-small`: `0.000000000000007969`
- `bcs_decode_pool-like-small`: `0.000000000000031854`
- `bcs_encode_bytes2048`: `0.000000000000066290`
- `bcs_decode_bytes2048`: `0.000000000000246964`

Raw byte state rows:

| Case | Delta |
| --- | ---: |
| `raw_state_read_bytes32` | `0.000000000000004086` |
| `raw_state_write_bytes32` | `0.000000000000005392` |
| `raw_state_read_bytes512` | `0.000000000000033065` |
| `raw_state_write_bytes512` | `0.000000000000021325` |
| `raw_state_read_bytes2048` | `0.000000000000125225` |
| `raw_state_write_bytes2048` | `0.000000000000068731` |

Generic state rows:

| Payload | Typed read | Typed write | BCS enc | BCS dec | Local write | Local read | X write | X read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `amount` | `0.000000000000002022` | `0.000000000000003358` | `0.000000000000000692` | `0.000000000000001841` | `0.000000000000004873` | `0.000000000000003523` | `0.000000000000018227` | `0.000000000000013950` |
| `account-amount` | `0.000000000000006217` | `0.000000000000005844` | `0.000000000000003084` | `0.000000000000007990` | `0.000000000000008496` | `0.000000000000009804` | `0.000000000000025468` | `0.000000000000020232` |
| `pool-like-small` | `0.000000000000020213` | `0.000000000000011683` | `0.000000000000007969` | `0.000000000000031854` | `0.000000000000018699` | `0.000000000000033668` | `0.000000000000051488` | `0.000000000000044096` |
| `bytes512` | `0.000000000000033073` | `0.000000000000021334` | `0.000000000000018889` | `0.000000000000062644` | `0.000000000000039251` | `0.000000000000064600` | `0.000000000000102058` | `0.000000000000075028` |
| `bytes2048` | `0.000000000000125233` | `0.000000000000068739` | `0.000000000000066290` | `0.000000000000246964` | `0.000000000000133725` | `0.000000000000248920` | `0.000000000000344108` | `0.000000000000259347` |

Typed read/write means the caller application reads or writes the business payload type directly in its own Linera view. Local write means the caller encodes the same sample payload to BCS bytes and writes those bytes in its own state. Local read means the caller reads seeded BCS bytes from its own state and decodes them. X write and X read are the corresponding `call_application` generic-state paths.

Caveat: single-operation BCS decode rows carry the encoded payload in the operation bytes, while local and cross-application read/decode rows read the encoded payload from state. The payload data is identical for each payload kind, but the data transport pattern is not identical for standalone decode.

Treat these as a reference snapshot, not a permanent protocol constant. Rerun the probe before making a design decision that depends on exact gas values.
