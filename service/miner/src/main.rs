// Copyright (c) Facebook, Inc. and its affiliates.
// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![recursion_limit = "256"]

#[cfg(feature = "jemalloc")]
#[global_allocator]
static ALLOC: tikv_jemallocator::Jemalloc = tikv_jemallocator::Jemalloc;

// jemalloc configuration for memory profiling with jemalloc_pprof
// prof:true,prof_active:true - Enable profiling from start
// lg_prof_sample:19 - Sample every 512KB for good detail/overhead balance

// Linux/other platforms: use unprefixed malloc (with unprefixed_malloc_on_supported_platforms)
#[cfg(all(feature = "memory-profiling", not(target_os = "macos")))]
#[allow(non_upper_case_globals)]
#[export_name = "malloc_conf"]
pub static malloc_conf: &[u8] = b"prof:true,prof_active:true,lg_prof_sample:19\0";

// macOS: use prefixed malloc (without unprefixed_malloc_on_supported_platforms)
#[cfg(all(feature = "memory-profiling", target_os = "macos"))]
#[allow(non_upper_case_globals)]
#[export_name = "_rjem_malloc_conf"]
pub static malloc_conf: &[u8] = b"prof:true,prof_active:true,lg_prof_sample:19\0";

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    path::PathBuf,
    process,
    sync::Arc,
};

use anyhow::{bail, ensure, Context, Error};
use async_trait::async_trait;
use chrono::Utc;
use clap_complete::generate;
use colored::Colorize;
use futures::{lock::Mutex, FutureExt as _, StreamExt as _};
use linera_base::{
    crypto::Signer,
    data_types::{ApplicationPermissions, Timestamp},
    identifiers::{AccountOwner, ChainId},
    listen_for_shutdown_signals,
    ownership::ChainOwnership,
    time::{Duration, Instant},
};
use linera_client::{
    chain_listener::{ChainListener, ChainListenerConfig, ClientContext as _},
    config::{CommitteeConfig, GenesisConfig},
};
use linera_core::{
    client::{ChainClientError, ListeningMode},
    data_types::ClientOutcome,
    wallet,
    worker::Reason,
    JoinSetExt as _, LocalNodeError,
};
use linera_execution::committee::Committee;
use linera_meme_miner::{benchmark::Benchmark as MinerBenchmark, miner::MemeMiner};
#[cfg(with_metrics)]
use linera_metrics::monitoring_server;
use linera_persistent::Persist;
use linera_storage::{DbStorage, Storage};
use linera_views::store::{KeyValueDatabase, KeyValueStore};

mod command;
mod options;

use crate::command::ClientCommand::{Benchmark, Run};
use options::Options;

use linera_service::{storage::Runnable, util};
use serde_json::Value;
use tempfile::NamedTempFile;
use tokio::{
    io::AsyncWriteExt,
    process::{ChildStdin, Command},
    sync::{mpsc, oneshot},
    task::JoinSet,
    time,
};
use tokio_util::sync::CancellationToken;
use tracing::{debug, error, info, warn, Instrument as _};

struct Job(Options);

fn read_json(string: Option<String>, path: Option<PathBuf>) -> anyhow::Result<Vec<u8>> {
    let value = match (string, path) {
        (Some(_), Some(_)) => bail!("cannot have both a json string and file"),
        (Some(s), None) => serde_json::from_str(&s)?,
        (None, Some(path)) => {
            let s = fs_err::read_to_string(path)?;
            serde_json::from_str(&s)?
        }
        (None, None) => Value::Null,
    };
    Ok(serde_json::to_vec(&value)?)
}

#[async_trait]
impl Runnable for Job {
    type Output = anyhow::Result<()>;

    async fn run<S>(self, storage: S) -> anyhow::Result<()>
    where
        S: Storage + Clone + Send + Sync + 'static,
    {
        let Job(mut options) = self;
        let mut wallet = options.wallet()?;
        let mut signer = options.signer()?;

        match &mut options.command {
            Run {
                meme_proxy_application_id,
                config,
            } => {
                assert!(
                    signer.keys().len() > 0,
                    "run `linera wallet init` and `linera wallet request-chain` to initialize wallet."
                );

                let meme_proxy_application_id = *meme_proxy_application_id;
                let mut config = config.clone();

                let mut context = options
                    .create_client_context(storage, wallet, signer.into_value())
                    .await?;
                let default_chain = context.default_chain();

                let _miner = Arc::new(
                    MemeMiner::new(
                        meme_proxy_application_id,
                        context,
                        &mut config,
                        default_chain,
                    )
                    .await,
                );

                let cancellation_token = CancellationToken::new();
                tokio::spawn(listen_for_shutdown_signals(cancellation_token.clone()));
                _miner.run(cancellation_token).await?;
            }
            Benchmark => {
                MinerBenchmark::benchmark();
            }
        }
        Ok(())
    }
}

async fn kill_all_processes(pids: &[u32]) {
    for &pid in pids {
        info!("Killing benchmark process (pid {})", pid);
        let _ = Command::new("kill")
            .arg("-9")
            .arg(pid.to_string())
            .status()
            .await;
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn init_tracing(
    options: &Options,
) -> anyhow::Result<Option<linera_base::tracing_opentelemetry::ChromeTraceGuard>> {
    linera_base::tracing::init(&options.command.log_file_name());
    Ok(None)
}

#[cfg(target_arch = "wasm32")]
fn init_tracing(options: &Options) {
    linera_base::tracing::init(&options.command.log_file_name());
}

fn main() -> anyhow::Result<process::ExitCode> {
    let options = Options::init();
    let mut runtime = if options.tokio_threads == Some(1) {
        tokio::runtime::Builder::new_current_thread()
    } else {
        let mut builder = tokio::runtime::Builder::new_multi_thread();

        if let Some(threads) = options.tokio_threads {
            builder.worker_threads(threads);
        }

        builder
    };

    // The default stack size 2 MiB causes some stack overflows in ValidatorUpdater methods.
    runtime.thread_stack_size(4 << 20);
    if let Some(blocking_threads) = options.tokio_blocking_threads {
        runtime.max_blocking_threads(blocking_threads);
    }

    let span = tracing::info_span!("linera::main");
    if let Some(wallet_id) = &options.with_wallet {
        span.record("wallet_id", wallet_id);
    }

    let result = runtime
        .enable_all()
        .build()?
        .block_on(run(&options).instrument(span));

    Ok(match result {
        Ok(0) => process::ExitCode::SUCCESS,
        Ok(code) => process::ExitCode::from(code as u8),
        Err(msg) => {
            error!("Error is {:?}", msg);
            process::ExitCode::FAILURE
        }
    })
}

async fn run(options: &Options) -> Result<i32, Error> {
    let _guard = init_tracing(options)?;
    match &options.command {
        _ => {
            options.run_with_storage(Job(options.clone())).await??;
            Ok(0)
        }
    }
}
