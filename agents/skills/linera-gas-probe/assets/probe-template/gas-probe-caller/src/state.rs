use gas_probe_abi::{AccountAmountPayload, PoolLikeSmallPayload};
use linera_sdk::{
    linera_base_types::Amount,
    views::{linera_views, MapView, RootView, ViewStorageContext},
};

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct GasProbeCallerState {
    pub bytes_by_size: MapView<u32, Vec<u8>>,
    pub amounts: MapView<u32, Amount>,
    pub account_amounts: MapView<u32, AccountAmountPayload>,
    pub pool_like_smalls: MapView<u32, PoolLikeSmallPayload>,
}
