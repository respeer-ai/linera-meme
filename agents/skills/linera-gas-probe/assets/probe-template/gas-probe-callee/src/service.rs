#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::GasProbeCalleeAbi;
use linera_sdk::{linera_base_types::WithServiceAbi, Service, ServiceRuntime};

pub struct GasProbeCalleeService;

linera_sdk::service!(GasProbeCalleeService);

impl WithServiceAbi for GasProbeCalleeService {
    type Abi = GasProbeCalleeAbi;
}

impl Service for GasProbeCalleeService {
    type Parameters = ();

    async fn new(_runtime: ServiceRuntime<Self>) -> Self {
        Self
    }

    async fn handle_query(&self, _request: Vec<u8>) -> Vec<u8> {
        Vec::new()
    }
}
