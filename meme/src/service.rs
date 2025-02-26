// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    base::{AccountOwner, Amount, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use meme::MemeOperation;

use self::state::MemeState;

pub struct MemeService {
    state: Arc<MemeState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(MemeService);

impl WithServiceAbi for MemeService {
    type Abi = meme::MemeAbi;
}

impl Service for MemeService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
                runtime: self.runtime.clone(),
            },
            MutationRoot {
                runtime: self.runtime.clone(),
            },
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl MutationRoot {
    async fn transfer(&self, to: AccountOwner, amount: Amount) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Transfer { to, amount });
        []
    }
}

struct QueryRoot {
    state: Arc<MemeState>,
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl QueryRoot {
    async fn total_supply(&self) -> Amount {
        self.state.meme.get().as_ref().unwrap().total_supply
    }

    async fn balance_of(&self, owner: AccountOwner) -> Amount {
        self.state.balances.get(&owner).await.unwrap().unwrap()
    }

    async fn native_balance_of(&self, owner: AccountOwner) -> Amount {
        self.runtime.owner_balance(owner)
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use abi::{
        meme::{InstantiationArgument, Meme, Metadata, Mint},
        store_type::StoreType,
    };
    use async_graphql::{Request, Response, Value};
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{AccountOwner, Amount, ApplicationId, Owner},
        util::BlockingWait,
        views::View,
        Service, ServiceRuntime,
    };
    use serde_json::json;
    use std::str::FromStr;

    use super::{MemeService, MemeState};

    #[tokio::test(flavor = "multi_thread")]
    async fn query() {
        let runtime = Arc::new(ServiceRuntime::<MemeService>::new());
        let mut state = MemeState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");

        let instantiation_argument = InstantiationArgument {
            meme: Meme {
                name: "Test Token".to_string(),
                ticker: "LTT".to_string(),
                decimals: 6,
                initial_supply: Amount::from_tokens(21000000),
                total_supply: Amount::from_tokens(21000000),
                metadata: Metadata {
                    logo_store_type: StoreType::S3,
                    logo: "Test Logo".to_string(),
                    description: "Test token description".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                },
            },
            mint: Some(Mint {
                fixed_currency: true,
                initial_currency: Amount::from_str("0.0000001").unwrap(),
            }),
            fee_percent: Some(Amount::from_str("0.2").unwrap()),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: None,
            proxy_application_id: None,
        };

        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str).unwrap();
        let application = AccountOwner::Application(application_id);
        state
            .instantiate(owner, application, instantiation_argument.clone())
            .await
            .expect("Failed inistantiate");

        let service = MemeService {
            state: Arc::new(state),
            runtime,
        };
        let request = Request::new("{ totalSupply }");

        let response = service
            .handle_query(request)
            .now_or_never()
            .expect("Query should not await anything");

        let expected = Response::new(
            Value::from_json(json!({"totalSupply" : instantiation_argument.meme.total_supply}))
                .unwrap(),
        );

        assert_eq!(response, expected)
    }
}
