<table>
  <tr>
    <td valign="middle" style="padding-right: 14px;">
      <div style="width: 64px; height: 64px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <img src="webui-v2/src/assets/Laugh.png" alt="MicroMeme logo" width="52" height="52" />
      </div>
    </td>
    <td valign="middle">
      <h1 style="margin: 0; line-height: 1.05;">MicroMeme</h1>
      <div style="font-size: 0.95rem; line-height: 1.2; padding-top: 4px;">Launch, trade, provide liquidity, and mine meme assets on Linera</div>
    </td>
  </tr>
</table>

[![Test](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml)

MicroMeme is a Linera-native meme market stack. The product goal is to combine simple meme launch, AMM trading, liquidity, mineable meme token mechanics, market data, and portfolio views.

The target is a full meme asset lifecycle on Linera:

1. Create a meme token.
2. Bootstrap a market.
3. Trade through AMM pools.
4. Add and manage liquidity.
5. Participate in mining-enabled issuance where supported.
6. Monitor prices, volume, positions, fees, and protocol activity from parsed chain facts.

## Business Architecture

MicroMeme has four product layers.

### Launch

`proxy/` and `meme/` coordinate meme creation, token state, mining configuration, and creation-time pool initialization.

### Exchange

`swap/` owns pool catalog and routing-facing registry state. `pool/` owns per-market AMM execution, reserves, LP accounting, and the target funding/claim accounting model.

### Mining

`meme/` owns mining state and reward semantics. `service/miner/` is an operational worker that submits mining operations; it is not product accounting truth.

### Market Data

`service/kline/` provides market data and portfolio-facing APIs such as transactions, candles, positions, volume, TVL, and protocol activity.

## Repository Layout

- `meme/`: meme token, balances, mining, redemption, and token-side transfer logic
- `swap/`: pool catalog, pool creation, and router-facing registry state
- `pool/`: AMM execution, reserves, liquidity, positions, and funding/claim target logic
- `proxy/`: meme creation orchestration and governance/product coordination
- `ams/`: application indexing and discovery support
- `blob-gateway/`: blob registration and metadata support
- `service/kline/`: market data, positions, candles, transactions, stats, and realtime APIs
- `service/miner/`: mining worker service
- `webui-v2/`: current primary frontend
- `docker/`: local compose deployment scripts
- `k8s/`: Kubernetes deployment assets
- `agents/`: assistant-facing rules, primitives, runbooks, and the only task board
- `documents/`: human-facing summaries, plans, and historical design notes

## Documentation

Canonical assistant-facing task and implementation guidance lives under [`agents/`](agents/):

- [AGENTS.md](AGENTS.md)
- [agents/README.md](agents/README.md)
- [agents/context/project-rules.md](agents/context/project-rules.md)
- [agents/tasks/board.yaml](agents/tasks/board.yaml)

Human-facing documents live under [`documents/`](documents/). These are summaries or planning notes; they are not the task source.
