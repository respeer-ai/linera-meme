// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::meme::InstantiationArgument;
use linera_sdk::{
    base::{AccountOwner, Amount, ApplicationPermissions, CryptoHash, Owner, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme::{MemeAbi, MemeError, MemeOperation, MemeResponse};
use proxy::{ProxyAbi, ProxyOperation};

use self::state::MemeState;

pub struct MemeContract {
    state: MemeState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(MemeContract);

impl WithContractAbi for MemeContract {
    type Abi = MemeAbi;
}

impl Contract for MemeContract {
    type Message = ();
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeContract { state, runtime }
    }

    async fn instantiate(&mut self, instantiation_argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        let owner = self.runtime.authenticated_signer().unwrap();
        self.state.instantiate(owner, instantiation_argument).await;

        self.change_application_permissions().await
    }

    async fn execute_operation(&mut self, operation: MemeOperation) -> MemeResponse {
        // TODO: Can only be run on users chain except Mine
        match operation {
            MemeOperation::Transfer { to, amount } => self
                .on_op_transfer(to, amount)
                .expect("Failed OP: transfer"),
            MemeOperation::TransferFrom { from, to, amount } => self
                .on_op_transfer_from(from, to, amount)
                .expect("Failed OP: trasnfer from"),
            MemeOperation::Approve { spender, amount } => self
                .on_op_approve(spender, amount)
                .expect("Failed OP: approve"),
            MemeOperation::BalanceOf { owner } => self
                .on_call_balance_of(owner)
                .expect("Failed Call: balance of"),
            MemeOperation::Mint { to, amount } => {
                self.on_op_mint(to, amount).expect("Failed OP: mint")
            }
            MemeOperation::TransferOwnership { new_owner } => self
                .on_op_transfer_ownership(new_owner)
                .expect("Failed OP: transfer ownership"),
            // Mine can only be run on creation chain
            MemeOperation::Mine { nonce } => self.on_op_mine(nonce).expect("Failed OP: mine"),
        }
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("Meme application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl MemeContract {
    async fn change_application_permissions(&mut self) {
        if let Some(proxy_application_id) = self.state.proxy_application_id().await {
            let application_id = self.runtime.application_id().forget_abi();
            let call = ProxyOperation::ChangeApplicationPermissions { application_id };
            let _ = self.runtime.call_application(
                true,
                proxy_application_id.with_abi::<ProxyAbi>(),
                &call,
            );
        }
    }

    fn on_op_transfer(
        &mut self,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_from(
        &mut self,
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_approve(
        &mut self,
        spender: AccountOwner,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_call_balance_of(&mut self, to: AccountOwner) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_mint(
        &mut self,
        to: Option<AccountOwner>,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_ownership(&mut self, owner: Owner) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_mine(&mut self, nonce: CryptoHash) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }
}

#[cfg(test)]
mod tests {
    use abi::{
        meme::{InstantiationArgument, Meme, Metadata, Mint},
        store_type::StoreType,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{Amount, ApplicationId, ChainId, Owner},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use meme::MemeAbi;
    use std::collections::HashMap;
    use std::str::FromStr;

    use super::{MemeContract, MemeState};

    #[test]
    fn operation() {}

    #[test]
    #[should_panic(expected = "Meme application doesn't support any cross-chain messages")]
    fn message() {
        let mut meme = create_and_instantiate_meme();

        meme.execute_message(())
            .now_or_never()
            .expect("Execution of meme operation should not await anything");
    }

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_meme() -> MemeContract {
        let operator =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let chain_id =
            ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46")
                .unwrap();
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str)
            .unwrap()
            .with_abi::<MemeAbi>();
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_can_change_application_permissions(true)
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_authenticated_signer(operator);
        let mut contract = MemeContract {
            state: MemeState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

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
            initial_balances: HashMap::new(),
        };

        contract
            .instantiate(instantiation_argument.clone())
            .now_or_never()
            .expect("Initialization of meme state should not await anything");

        assert_eq!(
            *contract.state.meme.get().as_ref().unwrap(),
            instantiation_argument.meme
        );
        assert_eq!(
            *contract.state.mint.get().as_ref().unwrap(),
            instantiation_argument.mint.unwrap()
        );
        assert_eq!(
            *contract.state.fee_percent.get().as_ref().unwrap(),
            instantiation_argument.fee_percent.unwrap()
        );

        contract
    }
}
