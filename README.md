![image](webui/src/assets/LineraMeme.svg)

# Linera Meme Microchain

[![Test](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/respeer-ai/linera-meme/actions/workflows/test.yml)

## Table of Contents
- [Microchain Introduction](#)
- [DeFi on Linera](#)
- [PoW Microchain](#)
- [Functionalities and Plans](#)
  - [SingleLeader Round Robin](#)
  - [MultiLeader Round Robin](#)
  - [Permissionless PoW/PoS Round](#)
  - [Meme Creation Setting](#)
- [Tokenomics of Meme Creators / Traders / Miners](#)

## Microchain Introduction

Microchain is concept derived from FastPay Account.

P2P methods like DHT and KAD are widely used in traditional blockchains. When a transaction is initiated, it is first broadcast to a mempool.
Validators then synchronize the mempool to their local memory and select appropriate transactions to construct the next block in the chain.
Because only one block can be added at each height by all validators, and the block capacity is limited by its size, validators must select
transactions based on preset conditions, such as the transaction fee. Consequently, if transactions with low fees need to be executed quickly,
users must increase their fees, which in turn increases the overall transaction costs across the network.

Linera redesigns the transaction execution workflow of blockchains. Instead of a monolithic blockchain, each account independently maintains
a full-function microchain. Transactions between different accounts are implemented using cross-chain RPC. When a transaction is created,
it is packed into a new block in the source microchain. Executing the block in the source microchain sends a message to the target microchain
through a local RPC. The target microchain then packs the message into a new block and executes it. A mempool, acting as a global cache, is
abandoned in Linera. Consequently, different validators and accounts do not compete for the same block space. This unlimited parallel execution
and deterministic cross-RPC invocation form the theoretical and engineering foundation for Linera to serve as the infrastructure for Web3
applications with Web2-level quality of service.

## DeFi on Linera

A microchain must be created by a chain owner. A block within a microchain is created only when needed, meaning the microchain does not have
a fixed block interval. A block will be proposed and submitted to validators when the chain owner(s) needs to create a transaction.

DeFi is a prominent application scenario for blockchain technology. Typically, an Automated Market Maker (AMM) protocol is adopted in DeFi
applications to balance supply and demand. Traders can earn profit by trading assets in a decentralized market. DeFi applications on traditional
blockchains are implemented as smart contracts, and the transactions within these applications are validated by the monolithic blockchain.
Because all transactions from all accounts are contained within a single monolithic blockchain, interactions between different accounts do
not require any special handling. While the introduction of Microchains solves the determinacy problem for Web3 applications, it also presents
new challenges. Because accounts are located on different microchains, and only chain owners can operate their respective microchains, applications
on a given microchain cannot be executed when the chain owner is offline. This limitation on chain owner control necessitates creative solutions
for DeFi applications on Linera.

## PoW Microchain

There is a type of microchain that can be controlled by multiple chain owners. This type of microchain can operate in two modes: Single-Leader and Multi-Leader.

When operating in Single-Leader mode, a leader is elected from the chain owners according to preset round and weight parameters. The elected leader
proposes new blocks and submits them to validators. However, Single-Leader mode has a potential issue: if the elected leader is offline during their
round, the round will time out and advance to the next round. This timeout is implemented with an evacuation algorithm that lacks an upper limit.
Consequently, if the offline chain owner cannot resume processing in time due to hardware failure or other unexpected issues, the microchain will be frozen.

In Multi-Leader mode, every chain owner can propose and submit blocks at any time. However, if multiple blocks are created at the same height,
all proposed blocks will be rejected, and the system will fall back to Single-Leader mode to elect a single leader to propose the new block.
There is no round timeout in Multi-Leader mode; any owner can propose their own block at any time.

Therefore, we have developed some new ideas regarding Multi-Leader microchains. Could we determine the unique block proposer using a Proof of Work,
Proof of Stake, or other mathematical algorithm? If the applications running on these microchains issue their own tokens and distribute token
rewards to block proposers, then we could establish a new method for issuing a minable meme token. Meme tokens on traditional blockchains are
typically implemented as smart contracts, with new tokens minted upon user deposit. The value of these meme tokens depends solely on the appeal
of the stories created by their originators. A minable meme token introduces a new value anchor, and also broadens the application scenarios for
Linera. Meme creators can still easily create memes. Simultaneously, the meme tokens can have intrinsic value derived from mining production.
The unique set of Linera validators ensures the security of the meme token, while fairness is ensured at the application layer.

The PoW microchain will be implemented as a pluggable subnet. This enables tailored DeFi application and microchain functionalities within Linera.
Applications that need to provide service to public users will no longer depend on chain owners' liveness; instead, they will be driven by a publicly
decentralized set of owners.

## Functionalities and Plans

### Stage 1: SingleLeader Round Robin

- [x] ABI definition
- [x] Meme Proxy framework
- [x] Miner registration and beneficiary account
- [x] Create meme chain and set application permission to allow meme proxy only
- [x] Create meme application on the meme chain
- [x] Update meme chain permissions to mandatory meme application only
- [x] Meme application fungible token
- [x] Meme application block rewards distribution
- [x] Swap application with dynamic liquidity pool
- [x] Liquidity pool application

### Stage 2: MultiLeader Round Robin

- [ ] Election leader with round robin - Election result must be same at each (round, height)

### Stage 3: Permissionless PoW/PoS Round

- [ ] Fix PoW difficulty
- [ ] PoW leader election - Election result must be same at each (round, height)
- [ ] Dynamic PoW difficulty
- [ ] PoS leader election - Election result must be same at each (round, height)

### Stage 4: Meme Creation Configuration

- [ ] Configure leader election method
- [ ] Configure block rewards / decay strategy
- [ ] Configure genesis miners airdrop strategy
- [ ] Configure initial liquidity pool strategy
- [ ] Configure developers lock strategy
- [ ] Configure whitelist lock strategy

### Stage 5: Meme Chain Open Eco-system

- [ ] Build open eco-system for meme chain to let user define their proxy with exists miners

## Tokenomics of Meme Creators / Traders / Miners

Meme creators can design their own tokens based on their unique vision.

Creators can configure the leader election method (PoW, PoS, etc.) for their meme token and even customize the PoW algorithm.
Perhaps one day, we can empower meme creators to define their own PoW or PoS algorithms. However, for now, we will simply
allow them to select from a set of preset algorithms to lower the barrier to entry.

In addition to the leader election algorithm, creators can configure the initial liquidity pool strategy, locking mechanisms,
and other parameters. Created meme tokens will then be listed on the Linera Swap DEX. Community members can join the meme
chain and propose blocks to earn block rewards.
