// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use std::borrow::Cow;

use linera_base::{data_types::Amount, identifiers::ApplicationId};
use linera_client::chain_listener::ChainListenerConfig;

// Proxy application ID of testnet conway
const TESTNET_CONWAY_PROXY_APPLICATION_ID: &str =
    "de63f511b1d3aaf20d4903739ef44000ed1b2ca5e16370de84eb1ad5719f2876";

#[derive(Clone, clap::Subcommand)]
pub enum ClientCommand {
    /// Miner for meme tokens
    Run {
        /// Meme proxy application id
        #[arg(
            long,
            default_value = TESTNET_CONWAY_PROXY_APPLICATION_ID,
            help = "Testnet conway proxy application id"
        )]
        proxy_application_id: ApplicationId,

        /// Configuration for the faucet chain listener.
        #[command(flatten)]
        config: ChainListenerConfig,
    },

    /// Run a benchmark for minier
    Benchmark,

    /// List all chains with balance
    ListBalances {
        /// Meme proxy application id
        #[arg(
            long,
            default_value = TESTNET_CONWAY_PROXY_APPLICATION_ID,
            help = "Testnet conway proxy application id"
        )]
        proxy_application_id: ApplicationId,
    },

    /// Redeem mining reward from meme chain to wallet chain
    Redeem {
        token: ApplicationId,
        amount: Option<Amount>,
    },
}

impl ClientCommand {
    /// Returns the log file name to use based on the [`ClientCommand`] that will run.
    pub fn log_file_name(&self) -> Cow<'static, str> {
        match self {
            ClientCommand::Run { .. } => "miner".into(),
            ClientCommand::Benchmark => "benchmark".into(),
            ClientCommand::ListBalances { .. } => "list_balances".into(),
            ClientCommand::Redeem { .. } => "redeem".into(),
        }
    }
}
