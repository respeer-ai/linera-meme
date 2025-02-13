# Linera Meme Microchain

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

## Functionalities and Plans

## Tokenomics of Meme Creators / Traders / Miners
