# Project Task Board

Type: Task Board
Audience: Coding assistants
Authority: High

## Status Legend

- `Todo`: not started
- `Doing`: in progress
- `Done`: completed
- `Blocked`: waiting on external confirmation or dependency

## Positions

| ID | 状态 | Priority | Depends On | 任务 | 说明 |
| --- | --- | --- | --- | --- | --- |
| POS-001 | Done | P2 | None | Positions tab / route | 页面入口已存在 |
| POS-002 | Done | P2 | POS-001 | Positions 原型页 | 当前为静态原型页 |
| POS-003 | Done | P2 | POS-002 | V2 文案语义校正 | 已去掉 V3 风格 `in range / rewards / incentives` |
| POS-004 | Done | P2 | POS-002 | Status UI 改成 `All / Active / Closed` | 当前仅 UI，尚未接真实数据 |
| POS-005 | Todo | P2 | None | 明确 `opened_at` 定义 | 取首次 add，还是最近一轮 reopen 时间 |
| POS-006 | Todo | P2 | POS-005 | 明确 `current_liquidity` 与 `LMM` 展示关系 | 是否直接用作顶部 share 数值 |
| POS-007 | Done | P1 | None | 在 `service/kline` 实现 `get_positions(owner, status)` | 已完成 owner 维度 positions 聚合查询 |
| POS-008 | Done | P1 | POS-007 | 在 `service/kline` 暴露 `GET /positions` | 已完成统一查询接口 |
| POS-009 | Done | P1 | POS-007 | 为 positions 聚合补 DB 单测 | 已覆盖 active / closed / 多池 / 多用户 / 非法状态 |
| POS-010 | Done | P1 | POS-008 | 为 `/positions` 补接口测试 | 已覆盖 owner / status / 非法参数 |
| POS-011 | Done | P1 | POS-008 | 前端新增 positions store/types/wrapper | 已新增独立 positions 数据层 |
| POS-012 | Done | P1 | POS-011 | Positions 页接钱包 owner | 已按当前钱包 owner 拉取 positions |
| POS-013 | Done | P1 | POS-008, POS-011, POS-012 | Positions 页接 `/positions` | 已拉取真实 active / closed 数据 |
| POS-014 | Done | P1 | POS-013 | 实现 `Status` 筛选联动接口 | 已支持 `all / active / closed` 查询切换 |
| POS-015 | Done | P1 | POS-013 | 实现真实列表渲染 | 已用真实 position card 替换纯空态原型 |
| POS-016 | Done | P2 | POS-015 | 空态区分“未连接钱包 / 无持仓” | 已区分钱包未连接、无 active、无 closed |
| POS-017 | Done | P2 | POS-015 | 设计 active position card | 已展示 pool、token、share、opened / activity 信息 |
| POS-018 | Done | P1 | POS-015 | 接 `Manage / Remove liquidity` 入口 | 已支持从 active position 进入 remove/manage 页面 |
| POS-019 | Blocked | P0 | None | 核验 `from_account` 是否稳定代表 LP owner | 依赖后端交易写库语义确认 |
| POS-020 | Blocked | P0 | None | 核验 `liquidity` 字段是否可直接净额相减 | 依赖后端字段单位和精度确认 |

## Contract Tests

| ID | 状态 | Priority | Depends On | 任务 | 说明 |
| --- | --- | --- | --- | --- | --- |
| TEST-004 | Done | P0 | None | 为 `pool` 补 fund 异步闭环异常测试 | 已覆盖第一笔成功第二笔失败、两笔成功但最终 `AddLiquidity` / `NewTransaction` 未闭环 |
| TEST-006 | Done | P0 | None | 为 `swap` 补 `UpdatePool` 幂等/乱序测试 | 已覆盖重复 transaction、旧 transaction 覆盖新状态、reserve/price 不回退 |
| TEST-001 | Done | P1 | None | 为 `pool` 补 `SetFeeTo / SetFeeToSetter` 权限测试 | 已覆盖 operator 正常路径、旧 operator 失效、非 operator 拒绝 |
| TEST-002 | Done | P1 | None | 为 `pool` 补 `RemoveLiquidity` 集成级历史断言 | 已覆盖 meme-native / meme-meme，要求 `latestTransactions` 出现 `RemoveLiquidity` |
| TEST-003 | Done | P1 | None | 为 `pool` 补 min amount 边界测试 | 已覆盖 `Swap / AddLiquidity / RemoveLiquidity` 的刚好满足、差 1 attos、不满足 |
| TEST-005 | Done | P1 | None | 为 `pool` 补 `NewTransaction` 幂等与 5000 条队列边界测试 | 已覆盖重复 message、4999/5000/5001 截断保序 |
| TEST-007 | Done | P1 | None | 为 `swap` 补 `CreatePool / CreateUserPool / UserPoolCreated / PoolCreated` 边界测试 | 已覆盖重复建池、同 token 建池、错链回执、重复回执 |
| TEST-012 | Done | P1 | None | 为 `meme` 补 `TransferFromApplication / InitializeLiquidity / TransferToCaller` 权限测试 | 已覆盖缺失 authenticated caller、错误 caller、重复初始化、余额边界 |
| TEST-013 | Done | P1 | None | 为 `meme` 补 `Mint / Redeem` 边界测试 | 已覆盖 `Mint` 非 owner signer 拒绝、`Redeem(None)` 全额赎回、`Redeem(Some(0))`、超额赎回 |
| TEST-008 | Done | P2 | None | 为 `proxy` 补 genesis miner remove 全链路测试 | 已在多链集成层覆盖 `ProposeRemoveGenesisMiner / ApproveRemoveGenesisMiner` 两阶段移除闭环 |
| TEST-009 | Done | P2 | None | 为 `proxy` 补 miner register/deregister 边界测试 | 已覆盖重复注册、未注册注销、跨 owner / 错链，并修正 deregister 静默 no-op 掩盖非法输入的问题 |
| TEST-010 | Done | P2 | None | 为 `proxy` 补 operator 治理测试 | 已覆盖 `Propose/Approve AddOperator` 与 `Propose/Approve BanOperator` 两阶段治理，并修正 operator 校验与 ban 审批状态写回问题 |
| TEST-011 | Done | P2 | TEST-010 | 为 `proxy` 补 `CreateMemeExt / MemeCreated` 异步幂等测试 | 已覆盖重复回执、错链回执、创建成功后状态写入，并修正 `MemeCreated` receipt 幂等处理 |
| TEST-014 | Done | P2 | None | 为 `ams` 补 contract/integration 基础测试 | 已补 `ams_contract` 基线测试，覆盖 `Register / Claim / AddApplicationType / Update` 的正常、重复、权限与非法类型输入，并将 `Claim` 恢复为基于 origin/runtime 的当前发起者语义 |
| TEST-015 | Done | P2 | None | 为 `blob-gateway` 补 contract/integration 基础测试 | 已覆盖 `Register` operation 发消息、message 落库、重复 hash 幂等且保留首条 metadata |
| REV-001 | Done | P2 | None | Review 当前资金闭环与退款一致性风险 | 已确认 3 类高风险缺口：`AddLiquidity` 双腿部分成功后失败无退款、pool payout/refund 吞掉 `MemeResponse::Fail`、初始建池路径吞掉下游失败仍持久化成功 |

## Funds Consistency

| ID | 状态 | Priority | Depends On | 任务 | 说明 |
| --- | --- | --- | --- | --- | --- |
| FUNDS-001 | Todo | P0 | REV-001 | 修复 `AddLiquidity` 双腿部分成功后的退款缺失 | 当前第一腿 `FundSuccess` 后第二腿 `FundFail` 只记失败，不把已锁定第一腿资金退回用户 |
| FUNDS-002 | Todo | P0 | REV-001 | 修复 pool payout / refund 对 `MemeResponse::Fail` 的静默吞错 | 涉及 swap 输出发放、swap refund、add-liquidity excess refund、remove-liquidity payout |
| FUNDS-003 | Todo | P0 | REV-001 | 修复初始建池链路的伪成功持久化 | `PoolCreated` / `LiquidityFunded` 等路径忽略下游 call 结果，可能出现 pool 已登记但初始资金或初始化未完成 |
| FUNDS-004 | Todo | P1 | REV-001 | 为资金闭环补集成测试 | 覆盖部分成功退款、输出发放失败、初始建池下游失败后的状态一致性 |
