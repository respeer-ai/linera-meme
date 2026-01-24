use std::sync::Arc;

use abi::proxy::Chain;
use async_graphql::{Request, Variables};
use linera_base::{data_types::Amount, identifiers::ApplicationId};
use linera_client::chain_listener::ClientContext;
use serde::Deserialize;

use crate::{errors::MemeMinerError, wallet_api::WalletApi};

#[derive(Debug, Deserialize)]
struct SwapResponse {
    #[allow(dead_code)]
    swap: Vec<u8>,
}

pub struct PoolApi<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,

    pool_application_id: ApplicationId,
}

impl<C> PoolApi<C>
where
    C: ClientContext + 'static,
{
    pub fn new(wallet: Arc<WalletApi<C>>, pool_application_id: ApplicationId) -> Self {
        Self {
            wallet,
            pool_application_id,
        }
    }

    pub async fn swap(
        &self,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
    ) -> Result<(), MemeMinerError> {
        let mut request = Request::new(
            r#"
            mutation swap($amount0In: Amount, $amount1In: Amount) {
                swap(amount0In: $amount0In, amount1In: $amount1In)
            }
            "#,
        );

        let mut variables_map = serde_json::Map::new();
        if let Some(amount_0_in) = amount_0_in {
            variables_map.insert("amount0In".to_string(), serde_json::json!(amount_0_in));
        }
        if let Some(amount_1_in) = amount_1_in {
            variables_map.insert("amount1In".to_string(), serde_json::json!(amount_1_in));
        }

        let variables_json = serde_json::Value::Object(variables_map);
        request = request.variables(Variables::from_json(variables_json));

        let hash = self
            .wallet
            .execute_operation::<SwapResponse>(
                self.pool_application_id,
                self.wallet.default_chain(),
                request,
            )
            .await?;
        tracing::info!("Hash {:?}", hash);
        Ok(())
    }
}
