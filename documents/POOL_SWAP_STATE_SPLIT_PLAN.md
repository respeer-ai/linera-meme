# Pool / Swap State App 拆分方案

## 0. 状态与适用范围

- 本文档固化 pool 和 swap 的 business/state app 拆分计划。
- 前置工作已完成：ams、blob-gateway、meme、proxy 四个应用已按同一模式完成拆分（见 `documents/MEME_STATE_SPLIT_PLAN.md` 与 git 历史）。
- 本文档只做设计与任务拆分；所有代码改动必须逐 diff 经 review 通过后才允许落代码（单 diff ≤ 50 行，一次 review 一个 handler）。

## 1. 设计原则（与 proxy/meme 完全一致）

- **business app 本地 state 只有两个 view**：`state_applications: MapView<u16, ApplicationId>` + `latest_state_version: RegisterView<u16>` + `EXPECTED_LATEST_STATE_VERSION` 常量；其余全部进 state app。
- **state app 结构**：`business_application_id` + `operator` + 全部业务数据。`instantiate` 存 `business_application_id` 与 `operator`。
- **state app 权限（meme 严格模型）**：所有 state operation 校验 `require_authenticated_caller_id() == state.business_application_id`（本链实例）。proxy/state 当前未做该校验，属遗留薄弱点，由 TSTATE-061 补齐。
- **state 只做状态更新 + 资金守卫**（余额不足、invariant 等检查放在 state op 内，同 meme state 的 transfer 检查）；业务计算（Uniswap-V2 数学、optimal amounts、编排）留在 business app。
- **ABI 与 crate 结构约束**：遵循 `agents/context/project-rules.md`：
  - `abi/src/<family>.rs` 只含 `pub mod` + `pub use` re-export；
  - operation/message 定义在 `abi/src/<family>/abi.rs`；state ABI 在 `abi/src/<family>/state_v1.rs`；
  - crate 拆分为 `<family>/app/`（package `<family>-app` 或保持短名，参照 proxy/app=proxy、meme/app=meme-app）与 `<family>/state/`（package `<family>-state`）；
  - operation/message enum 新变体只能 append 在末尾（BCS variant index 稳定）。
- **功能对齐 main HEAD**：拆分唯一允许的行为差异是 state 拆分本身（Initialize/AppendStates 流程）；权限、调用方向、资金语义、静默 no-op 行为必须与 main 完全一致。pool 侧适用 `pool/AGENTS.md` 的全部资金一致性规则。
- **standard operations**：每个 business app 实现 `Initialize`、`AppendState`、`AppendStates`、`Handoff`、`SetOperator`；Initialize 的调用方约束参照各应用实际业务（meme 由 proxy 调；swap/pool 由 linest/部署流程调）。

## 2. 已确认的关键设计决策

1. **swap 多链实例**：swap 同时存在于 creator chain 和每个 pool chain。state app 只挂 creator chain 实例；pool chain 实例不挂 state app，其 handler（`CreatePool` message、`UserPoolCreated`）不得触碰 catalog state（现状已是如此）；bytecode ids 经 message 传递。
2. **pool 由 swap 创建时同时创建 state app**（照搬 proxy→meme 的 `CreateMemeExt` 模式）：swap 记录 `pool_state_bytecode_ids`，create pool 时在 pool chain 上 create pool business app → create pool state app → `AppendStates` → `Initialize`。
3. **pool ABI 迁移**：`abi/src/swap/pool/` → `abi/src/pool/`（遵循 ams 结构约束），全部 `abi::swap::pool::*` 引用点同步改。
4. **state 操作粒度**：业务计算在 business app；state 做状态更新 + 资金守卫。具体 op 拆分在每个 handler 迁移时逐 diff 讨论。

## 3. Pool 拆分（Phase P1）

### 3.1 目录结构变更

```
abi/src/pool.rs                # 新增：纯 re-export 入口（同 ams.rs）
abi/src/pool/abi.rs            # 新增：从 abi/src/swap/pool/mod.rs 迁出
                               #   PoolOperation / PoolMessage / Pool（数学）/
                               #   PoolParameters / InstantiationArgument /
                               #   FundRequest / BootstrapPolicy / 各类 receipt
abi/src/pool/state_v1.rs       # 新增：PoolStateV1Operation / PoolStateV1Response /
                               #   StateInstantiationArgument
abi/src/swap/transaction.rs    # 迁移：Transaction/TransactionType 移入 pool 侧
                               #   （pool 产生、swap 消费），swap ABI re-export

pool/app/Cargo.toml            # package pool（保持短名，参照 proxy/app）
pool/app/src/                  # business app（由 pool/src/ 拆分迁移）
pool/state/Cargo.toml          # package pool-state
pool/state/src/                # state app
```

根 `Cargo.toml`：members 中 `"pool"` 替换为 `"pool/app"`、`"pool/state"`；`[workspace.dependencies]` 相应调整。

### 3.2 State app 内容（PoolState 全部成员进 state）

| 成员 | 说明 |
|---|---|
| `pool` | reserves / fee / fee_to / fee_to_setter / k_last / price cumulatives / timestamp |
| `router_application_id` | swap app id |
| `total_supply` | LP 总供给（含 fee 稀释的 effective supply 计算在 business/service 层） |
| `shares` | `MapView<Account, Amount>` LP 仓位 |
| `claimable_balances` | `MapView<MemeToken, HashMap<Account, Amount>>` 应付 |
| `claiming_balances` | 在途 claim |
| `transaction_id` | 计数器（历史本身在 swap/kline，不进链上 state） |

Uniswap-V2 数学（`liquid`、`mint_fee`、invariant、TWAP）是纯函数，留在 abi 的 `Pool` struct 与 business app。

### 3.3 创建流程（swap → pool，照搬 proxy→meme）

swap 的 create pool 在 pool chain 上：
1. create pool business app（`PoolParameters{creator, token_0, token_1, bootstrap_policy}` + `InstantiationArgument{pool_fee_percent_mul_100, router_application_id, amount_0_in, amount_1_in}`）；
2. create pool state app（`StateInstantiationArgument{business_application_id: <pool app id>, operator: <pool creator>}`）；
3. pool business `AppendStates{state_application_ids: [pool_state_app_id]}`；
4. pool business `Initialize{...}`（完成 pool 记录初始化等，具体参数在 handler 迁移时定）。

pool state bytecode id 来源：swap 的 `pool_state_bytecode_ids: MapView<u16, ModuleId>`（Initialize 传入 + `SetPoolBytecodeIds` operation 升级，多版本共存）。

### 3.4 任务拆分（board: TSTATE-041 ~ TSTATE-049）

- **TSTATE-041** ABI 迁移：`abi/src/pool/` 新建（`pool.rs` 入口 + `abi.rs` + `state_v1.rs` 骨架），`Transaction` 迁移，全部引用点改造（swap、pool、meme、proxy 测试、decoder）。
- **TSTATE-042** pool/state crate 骨架：Cargo.toml、目录、workspace 注册。
- **TSTATE-043** pool/state 核心：`PoolState` + `StateInterface` + instantiate + HandlerFactory + caller 校验骨架。
- **TSTATE-044** pool/state handlers 逐个迁移（settle add/remove/swap liquidity、claim 系列、fee、initialize）——一 handler 一 diff。
- **TSTATE-045** pool/state 单测：现有 state 相关单测迁移 + 负向 caller 测试。
- **TSTATE-046** pool/app 骨架：本地 state（两 view）、adapter（contract/service）、`Initialize`/`AppendState(s)`/`Handoff`/`SetOperator`。
- **TSTATE-047** pool/app handlers 迁移：11 operation + 13 message 逐个 diff；权限/链约束与 main HEAD 逐项对齐；`pool/AGENTS.md` 资金一致性规则逐条核对。
- **TSTATE-048** pool/app 单测迁移（约 60 个）。
- **TSTATE-049** pool 集成测试迁移：`tests/test_suite.rs` 适配（ProxyMemeSetup 增加 pool state app 部署）+ 4 个集成测试。

## 4. Swap 拆分（Phase P2，依赖 P1）

### 4.1 目录结构变更

```
abi/src/swap.rs                # 入口（现有 swap/mod.rs 改造，纯 re-export）
abi/src/swap/abi.rs            # 从 router.rs 迁出：SwapOperation / SwapMessage /
                               #   SwapResponse / router Pool / InstantiationArgument
abi/src/swap/state_v1.rs       # 新增：SwapStateV1Operation / SwapStateV1Response /
                               #   StateInstantiationArgument
abi/src/pool/                  # pool ABI（P1 已迁出，swap 侧删除 pool/ 与 transaction.rs）

swap/app/Cargo.toml            # package swap
swap/app/src/                  # business app
swap/state/Cargo.toml          # package swap-state
swap/state/src/                # state app
```

### 4.2 State app 内容（catalog 全部进 state）

| 成员 | 说明 |
|---|---|
| `meme_meme_pools` / `meme_native_pools` | pair → Pool catalog |
| `pool_id` | 计数器（起点 1000，Initialize 传入） |
| `pool_meme_memes` / `pool_meme_natives` | pool_id 反查索引 |
| `pool_bytecode_id` | pool business bytecode |
| `pool_state_bytecode_ids` | **新增**：`MapView<u16, ModuleId>`，创建 pool 时用 |
| `pool_chains` | 已开 pool chain 注册表（反欺骗） |

`token_creator_chain_ids` 为死代码，拆分中删除。

### 4.3 多链实例约束（决策 1）

- state app 只挂 creator chain 的 swap 实例（linest 部署 + AppendState + Initialize）。
- pool chain 实例无 state app：`CreatePool` message 继续携带 `pool_bytecode_id` + `pool_state_bytecode_ids`（message 结构相应扩展，变体 append）；pool chain handler 禁止调用 state adapter（代码评审红线）。
- `UpdatePool` / `PoolCreated` 等需要 catalog 的 handler 保持在 creator chain 执行（现状已是如此）。

### 4.4 任务拆分（board: TSTATE-051 ~ TSTATE-057）

- **TSTATE-051** ABI 迁移：`swap/mod.rs` → `swap.rs` 入口；`router.rs` → `swap/abi.rs`；新建 `swap/state_v1.rs`；删除 `swap/pool/` 与 `swap/transaction.rs`（P1 已迁）。
- **TSTATE-052** swap/state crate 骨架。
- **TSTATE-053** swap/state 核心 + handlers + 单测（catalog CRUD + `SetPoolBytecodeIds`）。
- **TSTATE-054** swap/app 骨架 + adapter + 标准 operations（含 `SetPoolBytecodeIds` 升级路径）。
- **TSTATE-055** swap/app handlers 迁移（含 create_pool 适配决策 2 的"pool 带 state app 创建"）。
- **TSTATE-056** swap/app 单测迁移（37 个）。
- **TSTATE-057** swap 集成测试迁移（meme_meme_pair、kline_e2e、4 个 meme_native_pair）。

## 5. 部署接入（Phase P3，依赖 P2）

- **TSTATE-058** linest 注册 pool/swap bytecode：pool 为 `bytecode_only`（参照 meme，swap 创建实例）；swap 为完整部署（business + state + AppendState + Initialize）。
- **TSTATE-059** run_local.sh 适配；swap `CreatePool` message 携带 state bytecode ids 的端到端打通。
- **TSTATE-060** 端到端验证：创建 pool → 加流动性 → swap → remove/claim → kline 出数据；与 main HEAD 行为逐项对照。

## 6. 并行小任务

- **TSTATE-061** proxy/state 补 caller 校验（对齐 meme 严格模型）+ 负向 UT。proxy/state 现有 UT 未约束 caller（runtime 未设置 authenticated_caller，无负向测试）。

## 7. 受影响方面清单（实施时逐项核对）

- **meme**：`initialize_liquidity` message 调 pool `InitializeLiquidity`；`transfer_from_application_receipt` 调 pool 3 个 receipt ops（调用对象是 pool business app，接口不变，仅 ABI 路径变更）。
- **proxy**：创建 meme 流程不涉及 pool ABI；proxy 测试 mock pool，适配 ABI 路径。
- **decoder**：`canonical_decoder` match PoolOperation 变体，路径同步。
- **webui-v2**：`stores/swap/` 消费 swap/pool service GraphQL，字段名保持不变。
- **kline**：从 pool chain service 读数据，service 层适配 state app 后字段不变。
- **pool/AGENTS.md**：拆分落地后更新 Primary Files 路径。
