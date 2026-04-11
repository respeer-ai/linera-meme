# Positions Page Implementation Plan

> Audience: humans
>
> This document is a feature plan and design note.
> It is not the task board.
> Live task tracking is maintained in `agents/tasks/board.yaml`.

## Background

当前 [`PositionsPage.vue`](../webui-v2/src/pages/PositionsPage.vue) 只是 UI 原型，已经具备：

- 顶部 tab / 路由入口
- V2 语义文案
- `Active / Closed` 状态筛选 UI
- 空仓状态样式

但还没有接入真实的用户持仓数据，因此暂时不能展示：

- 当前活跃仓位
- 已关闭仓位
- 每个仓位的池子信息
- 用户在各池中的 LP share / liquidity

## Goal

实现一个真实可用的 V2 `Positions` 页面，支持：

- 查询当前钱包用户的 `Active positions`
- 查询历史 `Closed positions`
- 支持 `status=active|closed|all` 过滤
- 后续可扩展到每个仓位的 `Manage / Remove liquidity`

## Design Principles

### 1. 合约层不直接维护 positions 列表

合约和链上应用只维护真实状态与事件，例如：

- 当前池子状态
- 用户 add / remove liquidity 操作
- 当前 owner 在某个 pool 中的 liquidity

前端页面需要的 `positions` 列表本质上是“面向用户的聚合视图”，不适合维护在协议状态里。

### 2. 由数据服务聚合 positions 视图

`service/kline` 已经记录了：

- `AddLiquidity`
- `RemoveLiquidity`
- `from_account`
- `liquidity`
- `pool_id`
- `pool_application`
- `created_at`

因此 `service/kline` 最适合作为 `positions` 聚合服务：

- 输出当前持仓
- 输出已关闭持仓
- 统一定义 `Active / Closed`

### 3. 前端只消费聚合结果

前端不应该自己遍历全量 pool 再逐个查 `liquidity(owner)` 来拼页面，因为：

- 成本高
- 难分页
- 无法稳定得到 `Closed positions`

前端应该直接调用统一的 `positions` API。

## Data Model And Aggregation

建议新增统一的 positions 响应结构：

```json
{
  "owner": "0x1234",
  "positions": [
    {
      "pool_id": 1001,
      "pool_application": "chain:owner",
      "token_0": "TOKENA",
      "token_1": "TOKENB",
      "status": "active",
      "current_liquidity": "123.450000000000000000",
      "added_liquidity": "200.000000000000000000",
      "removed_liquidity": "76.550000000000000000",
      "add_tx_count": 3,
      "remove_tx_count": 1,
      "opened_at": 1775800000000,
      "updated_at": 1775803000000,
      "closed_at": null
    }
  ]
}
```

聚合公式：

```text
added_liquidity = sum(AddLiquidity.liquidity)
removed_liquidity = sum(RemoveLiquidity.liquidity)
current_liquidity = added_liquidity - removed_liquidity
```

状态规则：

- `current_liquidity > 0` -> `active`
- `added_liquidity > 0 && current_liquidity = 0` -> `closed`

## API And Storage Sketch

保留原先 positions 聚合的 SQL / API 思路，作为人类可读方案。后续实现细节应以代码和 `agents/` 中的助手文档为准。

- `GET /positions?owner=...&status=active|closed|all`
- 聚合来源：`service/kline.transactions`
- 建议索引：`(from_account, transaction_type, pool_application, pool_id, created_at)`

## Testing Approach

应覆盖：

- DB 聚合测试
- API 测试
- 前端渲染测试

其中核心数据场景包括：

- 只有 add
- add 后部分 remove
- add 后完全 remove
- 多 pool
- 多用户同 pool
- 归零后重新 add
- 非 liquidity 交易不进入 positions
