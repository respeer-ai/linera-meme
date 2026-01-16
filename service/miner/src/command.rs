// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use std::{borrow::Cow, num::NonZeroU16, path::PathBuf};

use chrono::{DateTime, Utc};
use linera_base::{
    crypto::{AccountPublicKey, CryptoHash, ValidatorPublicKey},
    data_types::{Amount, BlockHeight, Epoch},
    identifiers::{Account, AccountOwner, ApplicationId, ChainId, ModuleId, StreamId},
    time::Duration,
    vm::VmRuntime,
};
use linera_client::{
    chain_listener::ChainListenerConfig,
    client_options::{
        ApplicationPermissionsConfig, ChainOwnershipConfig, ResourceControlPolicyConfig,
    },
    util,
};
use linera_rpc::config::CrossChainConfig;

// Proxy application ID of testnet conway
const TESTNET_CONWAY_MEME_PROXY_APPLICATION_ID: &str =
    "8d71c99af30539105874815b989b1ee71ddd89250f71e352b14d1390cfbd1172";

#[derive(Clone, clap::Subcommand)]
pub enum ClientCommand {
    /// Miner for meme tokens
    Run {
        /// Meme proxy application id
        #[arg(
            long,
            default_value = TESTNET_CONWAY_MEME_PROXY_APPLICATION_ID,
            help = "Testnet conway meme proxy application id"
        )]
        meme_proxy_application_id: ApplicationId,

        /// Configuration for the faucet chain listener.
        #[command(flatten)]
        config: ChainListenerConfig,
    },
    Benchmark,
}

impl ClientCommand {
    /// Returns the log file name to use based on the [`ClientCommand`] that will run.
    pub fn log_file_name(&self) -> Cow<'static, str> {
        match self {
            ClientCommand::Run { .. } => "miner".into(),
            ClientCommand::Benchmark => "benchmark".into(),
        }
    }
}
