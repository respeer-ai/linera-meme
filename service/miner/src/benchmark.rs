use std::{str::FromStr, time::Instant};

use abi::meme::MiningBase;
use linera_base::{
    crypto::CryptoHash,
    data_types::BlockHeight,
    identifiers::{AccountOwner, ChainId},
};

pub struct Benchmark;

impl Benchmark {
    pub fn benchmark() {
        let mining_base = MiningBase {
            height: BlockHeight(0),
            nonce: CryptoHash::from_str(
                "b0ba056f4eb7638df1dfe5affc893aa1d4b7922bb6bdf79bdb3623cfca624f12",
            )
            .unwrap(),
            chain_id: ChainId::from_str(
                "b0ba056f4eb7638df1dfe5affc893aa1d4b7922bb6bdf79bdb3623cfca624f12",
            )
            .unwrap(),
            signer: AccountOwner::from_str(
                "0xfd90bbb496d286ff1227b8aa2f0d8e479d2b425257940bf36c4338ab73705ac6",
            )
            .unwrap(),
            previous_nonce: CryptoHash::from_str(
                "b0ba056f4eb7638df1dfe5affc893aa1d4b7922bb6bdf79bdb3623cfca624f12",
            )
            .unwrap(),
        };

        let start_time = Instant::now();
        let mut n = 0usize;

        while start_time.elapsed().as_secs() < 60 {
            let _ = CryptoHash::new(&mining_base);
            n += 1;
        }

        tracing::info!("Hashes/S = {}", n / 60);
    }
}
