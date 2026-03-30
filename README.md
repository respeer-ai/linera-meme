<table>
  <tr>
    <td valign="middle" style="padding-right: 14px;">
      <div style="width: 64px; height: 64px; border-radius: 12px; display: flex; align-items: center; justify-content: center;">
        <img src="webui-v2/src/assets/Laugh.png" alt="MicroMeme logo" width="52" height="52" />
      </div>
    </td>
    <td valign="middle">
      <h1 style="margin: 0; line-height: 1.05;">MicroMeme</h1>
      <div style="font-size: 0.95rem; line-height: 1.2; padding-top: 4px;">Creating . Trading . Mining Meme on Linera</div>
    </td>
  </tr>
</table>

[![Test](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml)

MicroMeme is a Linera-native product that combines:

- Pump.fun-style meme launch,
- Uniswap-style exchange infrastructure,
- and mineable meme markets.

The target is a full meme asset lifecycle on Linera:

1. Create a meme.
2. Bootstrap a market.
3. Trade it.
4. Add liquidity.
5. Join mining.
6. Monitor market activity.

## Current Scope

This repository already contains the foundations for:

- meme creation,
- proxy and miner coordination,
- swap and pool applications,
- liquidity operations,
- K-line and transaction indexing,
- mineable meme token mechanics,
- frontend and service components.

## Current Priorities

- trading execution symmetry,
- mining-aware execution behavior,
- trustworthy quote infrastructure,
- multi-hop routing,
- launch UX simplification,
- mining-aware market data and user experience.

## Documents

Planning and architecture documents live under [documents/](documents/):

- [MICROMEME_PRODUCT_PLAN.md](documents/MICROMEME_PRODUCT_PLAN.md)
- [MICROMEME_TECHNICAL_ROADMAP.md](documents/MICROMEME_TECHNICAL_ROADMAP.md)
- [ARCHITECTURE.md](documents/ARCHITECTURE.md)

## Repository Layout

- `meme/`: meme token and mining logic.
- `swap/`: swap router state and pool registry.
- `pool/`: pool contract and swap/liquidity execution.
- `proxy/`: meme creation and miner-facing coordination.
- `service/kline/`: market data, transactions, and K-line service.
- `service/miner/`: mining worker service.
- `webui-v2/`: current web product UI.

## Product Layers

MicroMeme is evolving across three connected layers:

- Launch Layer: meme creation and market bootstrap.
- Exchange Layer: swap, routing, liquidity, and pricing.
- Mining Layer: mineable token issuance and miner participation.

## Why Linera

Linera's microchain execution model makes cross-chain settlement explicit and highly parallel. MicroMeme is built to use that model for:

- meme launch,
- exchange infrastructure,
- and mining-native token mechanics.

## Status

This project is functional but still evolving toward the full target product.

The largest remaining work is in execution semantics, quote and routing infrastructure, mining-aware product behavior, and creator launch UX.
