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
   - direct typed local state read/write for business payloads
   - raw byte state read/write as auxiliary byte-size reference
   - local generic state BCS encode/write and read/decode
   - `call_application` generic state BCS encode/write and read/decode
11. Stop the local GraphQL service.
12. Delete temporary probe directories unless the user asks to keep them.

## Measurement Matrix

- Baseline: `noop`
- BCS payload kinds: `amount`, `account`, `account-amount`, `pool-like-small`, `bytes32`, `bytes128`, `bytes512`, `bytes2048`
- BCS cases: encode x100 and decode x100 only; do not include encode+decode mixed cases
- `call_application` cases: noop x1/x10/x100
- Echo sizes: 0, 32, 128, 512, 2048 bytes with x1/x10
- `call_application` decode cases: `amount`, `account-amount`, `pool-like-small`, `bytes512`, `bytes2048` with x1/x10
- Direct typed local state cases:
  - `typed_state_read_<payload>_xN`
  - `typed_state_write_<payload>_xN`
- Raw byte state cases: `raw_state_read_bytes<bytes>_xN` and `raw_state_write_bytes<bytes>_xN` for 32, 512, and 2048 bytes with x1/x10
- Local generic state cases:
  - `generic_state_bcs_encode_write_<payload>_xN`
  - `generic_state_read_bcs_decode_<payload>_xN`
- Cross-application generic state cases:
  - `call_application_generic_state_bcs_encode_write_<payload>_xN`
  - `call_application_generic_state_read_bcs_decode_<payload>_xN`
- Generic payload kinds: `amount`, `account-amount`, `pool-like-small`, `bytes512`, `bytes2048` with x1/x10
- State read x10 cases must use distinct seeded storage keys per iteration.
- State write x10 cases must use distinct storage keys per iteration.

## Generic State Comparisons

Use these rows together for generic state design decisions:

- Direct typed read cost: `typed_state_read_<payload>_xN`
- Direct typed write cost: `typed_state_write_<payload>_xN`
- Raw byte read cost: `raw_state_read_bytes<bytes>_xN`
- Raw byte write cost: `raw_state_write_bytes<bytes>_xN`
- Pure encode cost: `bcs_encode_<payload>_x100`
- Pure decode cost: `bcs_decode_<payload>_x100`
- Local generic write cost: `generic_state_bcs_encode_write_<payload>_xN`
- Local generic read cost: `generic_state_read_bcs_decode_<payload>_xN`
- Cross-app generic write cost: `call_application_generic_state_bcs_encode_write_<payload>_xN`
- Cross-app generic read cost: `call_application_generic_state_read_bcs_decode_<payload>_xN`

Semantics:

- Direct typed state rows read or write the business payload type in the caller application state without an explicit business-level BCS conversion step.
- Raw byte state rows read or write `Vec<u8>` state without business-level BCS encode/decode; use them only as auxiliary byte-size references.
- Local generic write encodes a typed payload to bytes, then writes those bytes into state.
- Local generic read reads bytes from state, then decodes into the typed payload.
- Cross-app generic write calls the generic state application; the callee writes already encoded bytes to state.
- Cross-app generic read calls the generic state application; the callee reads bytes and decodes them.
- Use `call_application_noop_xN` to reason about the fixed call overhead separately.

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

Conway measurement on 2026-06-23 with isolated wallet `/tmp/gas-probe-conway-1782202027` produced these reference observations. BCS mixed encode+decode rows are intentionally omitted from the current matrix.

Environment:

- Chain: `f122b9c7c1108c2115a240de72da38459a808779a0ad30e03d9583852bb2a4eb`
- Callee app: `77c694e49bca44e8b8d035df1627bb2bbb18bbe962b13107c05a7a52c934c160`
- Caller app: `02c5716436e9480fd4cda72c719b1160b4a5b8eadc67c02a747382806e17a7c0`
- Callee module: `7c4682c92cc82510b6c81e0035da5da6e6756234a2de778c9e4c6f01f47070f67f7dbc32f214d171dcd88e8aaab7c8b66806dd81fa6439ed8d66eac7e28e135600`
- Caller module: `14388d36519185924f02d45df70d56904de2ec70951cd150b13799b0eba779648e8cfe9b4d5d44dd3095e7767b8ecfc1cad84b87e2a75726d3dc85c0566368a500`
- Local client: Linera v0.15.15; Conway faucet reported Linera v0.15.19 with matching WIT API hash.

Selected rows:

- `noop`: `0.000000000000020040`
- `call_application_noop_x100` delta per iteration: `0.000000000000003008`
- `bcs_encode_amount_x100` delta per iteration: `0.000000000000000594`
- `bcs_decode_amount_x100` delta per iteration: `0.000000000000000432`
- `bcs_encode_pool-like-small_x100` delta per iteration: `0.000000000000007871`
- `bcs_decode_pool-like-small_x100` delta per iteration: `0.000000000000018815`
- `bcs_encode_bytes2048_x100` delta per iteration: `0.000000000000066192`
- `bcs_decode_bytes2048_x100` delta per iteration: `0.000000000000124755`

Raw byte state rows, per iteration after subtracting `noop`:

| Case | x1 | x10 |
| --- | ---: | ---: |
| `raw_state_read_bytes32` | `0.000000000000004277` | `0.000000000000004024` |
| `raw_state_write_bytes32` | `0.000000000000005791` | `0.000000000000004989` |
| `raw_state_read_bytes512` | `0.000000000000033256` | `0.000000000000033003` |
| `raw_state_write_bytes512` | `0.000000000000024605` | `0.000000000000022564` |
| `raw_state_read_bytes2048` | `0.000000000000125416` | `0.000000000000125163` |
| `raw_state_write_bytes2048` | `0.000000000000080695` | `0.000000000000075509` |

Generic state rows, x10 per iteration after subtracting `noop`:

| Payload | Typed read | Typed write | BCS encode | BCS decode | Local encode+write | Local read+decode | Cross-app encode+write | Cross-app read+decode |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `amount` | `0.000000000000002020` | `0.000000000000002886` | `0.000000000000000594` | `0.000000000000000432` | `0.000000000000004494` | `0.000000000000003483` | `0.000000000000011351` | `0.000000000000007379` |
| `account-amount` | `0.000000000000006235` | `0.000000000000005394` | `0.000000000000002986` | `0.000000000000004693` | `0.000000000000007784` | `0.000000000000009764` | `0.000000000000018601` | `0.000000000000013660` |
| `pool-like-small` | `0.000000000000020227` | `0.000000000000011485` | `0.000000000000007871` | `0.000000000000018815` | `0.000000000000018187` | `0.000000000000033628` | `0.000000000000045033` | `0.000000000000037594` |
| `bytes512` | `0.000000000000033044` | `0.000000000000021128` | `0.000000000000018791` | `0.000000000000031673` | `0.000000000000040212` | `0.000000000000064560` | `0.000000000000098319` | `0.000000000000068534` |
| `bytes2048` | `0.000000000000125204` | `0.000000000000068533` | `0.000000000000066192` | `0.000000000000124755` | `0.000000000000144729` | `0.000000000000248880` | `0.000000000000346040` | `0.000000000000252853` |

Typed read/write means the caller application reads or writes the business payload type directly in its own Linera view. Cross-app encode+write means the caller BCS-encodes the typed payload, calls the generic state app with bytes, and the callee writes those bytes. Cross-app read+decode means the caller calls the generic state app, and the callee reads bytes and BCS-decodes them.

Treat these as a reference snapshot, not a permanent protocol constant. Rerun the probe before making a design decision that depends on exact gas values.
