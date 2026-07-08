# linest 设计与实现约定

> 本文件固化 2026-07-07 关于 `linest` 部署/升级工具的讨论结论。

## 1. 定位与边界

- `linest` 是 **Linera typed-state 应用的本地部署/升级 CLI 工具**。
- 只负责单个应用家族（app family）的部署与升级，不一次性部署整个集群。
- 通过调用本地 `linera` 客户端与链上 GraphQL service 完成工作。
- 命名：`linest`（Linera Estuary）。
- 安装方式：`pip install -e .`，以 `linest` 命令行入口运行。

## 2. 目录与持久化

- 默认基础目录：`~/.config/micromeme`
- 网络配置：`~/.config/micromeme/networks/<env>/config.json`
- 部署注册表：`~/.config/micromeme/deployments/<env>/<family>.json`
- 注册表写入使用 **write-temp-then-rename**，保证原子性。
- 注册表是链上状态的缓存；链上状态为权威来源。

## 3. 网络配置（每个环境一份）

```json
{
  "operator": "<Account 字符串，用于实例化 state app>",
  "query_service_url": "<统一查询 endpoint>",
  "wallet_dir": "<linera wallet 目录>",
  "wallet_services": {
    "ams": "<ams wallet service url>",
    "pool": "<pool wallet service url>"
  }
}
```

- `operator`：同一环境下所有应用家族共用同一个 operator，避免空态；部署 state app 时写入 `StateInstantiationArgument.operator`。
- `query_service_url`：只读查询统一入口。
- `wallet_services`：每个 app family 一个 mutation/交易 endpoint。

## 4. CLI

```bash
linest app deploy --name ams --version 1 --env local \
  --contract-bytecode PATH \
  --service-bytecode PATH \
  --state-contract-bytecode PATH \
  --state-service-bytecode PATH

linest app deploy --name ams --version 2 --env local
linest app status --name ams --env local
```

- `--base-dir` 可覆盖默认注册表目录。
- `--dry-run` 只打印计划步骤 + 状态比对，不执行任何链上操作。

## 5. 升级判定

工具通过以下规则判断是首次部署还是升级：

1. 读注册表。
2. 用注册表中的 business app id query 链上 `latestStateVersion` 与 `stateApplications`。
3. 若两者都为空 → 首次部署。
4. 否则 → 按当前最高版本 `N` 升级到 `N+1`。

允许链上已有 business app 但 `latestStateVersion == 0` 的半完成状态：工具会自动部署 v1 state app 并 `appendState`。

## 6. 标准升级流程

```
deploy new business app (vN+1)
deploy new state app (vN+1)
appendState(state_app_id_N+1)   // 通过 AMS app mutation
handoff(new_business_app_id)    // 通过 AMS app mutation
update registry
```

- `appendState` / `handoff` 通过 AMS business app 的 GraphQL mutation 触发：
  - `appendState(stateApplicationId: String!)`
  - `handoff(newBusinessApplicationId: String!)`
- 状态探测 query：
  - `latestStateVersion`
  - `stateApplications { version applicationId }`
  - state app 上的 `businessApplicationId`

## 7. 中断恢复（以链上为准）

假设目标版本为 `N+1`：

| 链上状态 | 含义 | 恢复动作 |
|---|---|---|
| `stateApplications` 仅到 `N` | `appendState` 未执行 | 部署 vN+1 state app → appendState → handoff |
| `stateApplications` 含 `N+1`，但 `businessApplicationId` 仍为旧 app | appendState 成功，handoff 失败 | 直接补 handoff |
| `stateApplications` 含 `N+1`，且 `businessApplicationId` 已是新 app | handoff 已完成，注册表未更新 | 只更新注册表 |

## 8. Bytecode 与 Module ID

- 工具本地计算 wasm 文件的 **sha256** 作为 `bytecode_hash`，存入注册表，用于检测“代码是否变化”。
- 链上真正的 `module_id` 由 `linera publish-bytecode` / `linera create-application` 返回，工具一并存入注册表。
- Linera `ModuleId` 由 contract/service bytecode 的 `BlobContent` 经 **Keccak256** 哈希组成；因为涉及压缩与 BCS 序列化，工具不自行复算。

## 9. Operator

- 不修改合约代码。
- 部署 state app 时，`StateInstantiationArgument.operator` 使用网络配置中的 `operator`（部署者/ creator 账户），不允许空态。
- operator 在所有 app family 间共享，只存网络配置，不重复存注册表。

## 10. 编码约束

- Python 代码使用面向对象风格。
- 每个文件只包含一个主导 class（辅助 dataclass 除外）。
- 单个文件不超过 500 行。

## 11. CLI 重试策略

- `publish-module` / `create-application` 等本地 `linera` CLI 调用统一走 `RetryPolicy`。
- 默认最多重试 3 次，遇到以下关键字视为可重试错误：
  - `A different block was already committed`
  - `Client failed to propose block`
  - `Timeout` / `timed out`
  - `Connection refused`
- 致命错误（如 bytecode 格式非法）不重试，立即抛出。

## 12. 未来命令：`linest bootstrap`（仅记录，暂不实现）

`bootstrap` 用于一次性部署整个环境的所有应用家族与 wallet 集群。它不属于 `linest app deploy` 的单一职责范围，需要更高层的编排。当前先记录需求，不开发：

- 读取环境配置，依次部署多个 app family。
- 管理 wallet 集群的初始创建、分发与注册。
- 处理跨应用依赖（如 pool 依赖 ams 的 state app）。
- 与 `linest app deploy` 共用同一套注册表与网络配置，但增加环境级编排状态。

## 13. 待实现清单

- [x] 项目骨架、CLI、注册表、模型
- [x] AMS app/state service 增加升级所需 mutation/query
- [x] `DeployCommand` 完整编排（探测 → 部署 → appendState → handoff → 写注册表）
- [x] `QueryClient` 对接 GraphQL
- [x] `LineraClient` 对接 `linera` 子命令
- [x] CLI 调用重试策略
- [x] dry-run 输出
- [x] 单元测试
- [ ] `linest bootstrap` 环境级部署编排（暂不实现）
- [ ] E2E 验证（依赖运行时环境）
