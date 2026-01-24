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

use std::{process, sync::Arc};

use anyhow::Error;
use async_trait::async_trait;
use linera_base::listen_for_shutdown_signals;
use linera_meme_miner::{benchmark::Benchmark as MinerBenchmark, miner::MemeMiner};
#[cfg(with_metrics)]
use linera_metrics::monitoring_server;
use linera_persistent::Persist;
use linera_storage::Storage;

use linera_meme_miner::{
    command::ClientCommand::{Benchmark, List, Redeem, Run},
    options::Options,
};

use linera_service::storage::Runnable;
use tokio_util::sync::CancellationToken;
use tracing::{error, Instrument as _};

struct Job(Options);

#[async_trait]
impl Runnable for Job {
    type Output = anyhow::Result<()>;

    async fn run<S>(self, storage: S) -> anyhow::Result<()>
    where
        S: Storage + Clone + Send + Sync + 'static,
    {
        let Job(mut options) = self;
        let wallet = options.wallet()?;
        let signer = options.signer()?;

        match &mut options.command {
            Run {
                proxy_application_id,
                config,
                with_maker,
                swap_application_id,
            } => {
                assert!(
                    signer.keys().len() > 0,
                    "run `linera wallet init` and `linera wallet request-chain` to initialize wallet."
                );

                let proxy_application_id = *proxy_application_id;
                let mut config = config.clone();
                let with_maker = *with_maker;
                let swap_application_id = swap_application_id.clone();

                let context = options
                    .create_client_context(storage, wallet, signer.into_value())
                    .await?;
                let default_chain = context.default_chain();

                let _miner = Arc::new(
                    MemeMiner::new(
                        proxy_application_id,
                        context,
                        &mut config,
                        default_chain,
                        with_maker,
                        swap_application_id,
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
            List => {
                tracing::info!("Not implemented");
            }
            Redeem { token, amount } => {
                tracing::info!("Not implemented");
            }
        }
        Ok(())
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
