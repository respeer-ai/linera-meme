#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::GasProbeCallerAbi;
use linera_sdk::{linera_base_types::WithServiceAbi, Service, ServiceRuntime};

pub struct GasProbeCallerService;

linera_sdk::service!(GasProbeCallerService);

impl WithServiceAbi for GasProbeCallerService {
    type Abi = GasProbeCallerAbi;
}

impl Service for GasProbeCallerService {
    type Parameters = ();

    async fn new(_runtime: ServiceRuntime<Self>) -> Self {
        Self
    }

    async fn handle_query(&self, _request: Vec<u8>) -> Vec<u8> {
        Vec::new()
    }
}
