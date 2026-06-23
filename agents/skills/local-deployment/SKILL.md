# Local Deployment Skill

Type: Skill
Audience: Coding assistants
Authority: High

## Purpose

Default workflow and invariants for local docker deployment.

## Facts

- Local deployment is driven by `docker/compose.sh`
- Local restart is driven by `docker/restart.sh`
- Local directory-specific rules live in [`../../../docker/AGENTS.md`](../../../docker/AGENTS.md)
- Inputs:
  - desired local deployment or restart change
  - docker compose files
  - wallet and query routing requirements
- Outputs:
  - working local environment aligned with k8s read/write split
  - validated startup order and wallet usage
- Stop Conditions:
  - local startup path is corrected and validated
  - or an external environment blocker remains

## Rules

- Local compose must mirror k8s read/write separation semantics
- Query service and maker wallet must use separate wallets
- Do not design startup flows that read wallets after the corresponding wallet-locking service has started
- Carry required owner and chain metadata forward from pre-start initialization instead of re-reading locked wallets later
- External network access for assistant-run commands should use the environment proxy selected by local LAN IP:
  - if local IP is `10.1.29.xxx`, use `socks5://10.1.29.96:7897`
  - if local IP is `192.168.31.xxx`, use `socks5://192.168.31.178:7897`
- Do not hardcode those proxy addresses into implementation scripts; pass them from the command environment when needed.

## Checklist

- Query service starts before dependent read traffic uses it
- Required multi-owner chains are imported into query before services depend on query reads
- Mutation services still own writes
- Business hosts remain unchanged in service config
- Local infra rewires DNS or proxying instead of mutating application-level hosts
