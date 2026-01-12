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

#[derive(Clone, clap::Subcommand)]
pub enum ClientCommand {
    /// Miner for meme tokens
    MemeMiner {
        /// Meme proxy application id
        #[arg(long)]
        meme_proxy_application_id: ApplicationId,

        /// Configuration for the faucet chain listener.
        #[command(flatten)]
        config: ChainListenerConfig,
    },
}

impl ClientCommand {
    /// Returns the log file name to use based on the [`ClientCommand`] that will run.
    pub fn log_file_name(&self) -> Cow<'static, str> {
        match self {
            ClientCommand::MemeMiner { .. } => "meme-miner".into(),
        }
    }
}
