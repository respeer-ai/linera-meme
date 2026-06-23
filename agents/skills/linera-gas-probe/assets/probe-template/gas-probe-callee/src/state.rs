use linera_sdk::views::{linera_views, MapView, RootView, ViewStorageContext};

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct GasProbeCalleeState {
    pub bytes_by_size: MapView<u32, Vec<u8>>,
}
