// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{
        InstantiationArgument, MemeAbi, MemeMessage, MemeOperation, MemeParameters, MemeResponse,
    },
    swap::router::{SwapAbi, SwapOperation},
};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ApplicationId, CryptoHash, Owner, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme::MemeError;
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
    type Message = MemeMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = MemeParameters;

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
        let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
        self.state
            .instantiate(owner, application, instantiation_argument)
            .await
            .expect("Failed instantiate");

        self.register_application().await;
        self.register_logo().await;
        self.change_application_permissions().await;

        // When the meme application is created, initial liquidity should already be funded
        self.create_liquidity_pool().await;
    }

    async fn execute_operation(&mut self, operation: MemeOperation) -> MemeResponse {
        if !self.operation_executable(&operation) {
            panic!("Operations must be run on right chain");
        }

        match operation {
            MemeOperation::Transfer { to, amount } => self
                .on_op_transfer(to, amount)
                .expect("Failed OP: transfer"),
            MemeOperation::TransferFrom { from, to, amount } => self
                .on_op_transfer_from(from, to, amount)
                .expect("Failed OP: trasnfer from"),
            MemeOperation::Approve {
                spender,
                amount,
                rfq_application,
            } => self
                .on_op_approve(spender, amount, rfq_application)
                .expect("Failed OP: approve"),
            MemeOperation::TransferOwnership { new_owner } => self
                .on_op_transfer_ownership(new_owner)
                .expect("Failed OP: transfer ownership"),
            MemeOperation::Mine { nonce } => self.on_op_mine(nonce).expect("Failed OP: mine"),
        }
    }

    async fn execute_message(&mut self, message: MemeMessage) {
        // All messages must be run on creation chain side
        if self.runtime.chain_id() != self.runtime.application_id().creation.chain_id {
            panic!("Messages must only be run on creation chain");
        }

        match message {
            MemeMessage::Transfer { to, amount } => self
                .on_msg_transfer(to, amount)
                .await
                .expect("Failed MSG: transfer"),
            MemeMessage::TransferFrom { from, to, amount } => self
                .on_msg_transfer_from(from, to, amount)
                .expect("Failed MSG: trasnfer from"),
            MemeMessage::Approve {
                spender,
                amount,
                rfq_application,
            } => self
                .on_msg_approve(spender, amount, rfq_application)
                .await
                .expect("Failed MSG: approve"),
            MemeMessage::Approved { rfq_application } => self
                .on_msg_approved(rfq_application)
                .expect("Failed MSG: approved"),
            MemeMessage::Rejected { rfq_application } => self
                .on_msg_rejected(rfq_application)
                .expect("Failed MSG: rejected"),
            MemeMessage::TransferOwnership { new_owner } => self
                .on_msg_transfer_ownership(new_owner)
                .expect("Failed MSG: transfer ownership"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl MemeContract {
    async fn register_application(&mut self) {
        if let Some(ams_application_id) = self.state.ams_application_id().await {
            // TODO: register application to ams
        }
    }

    async fn register_logo(&mut self) {
        if let Some(blob_gateway_application_id) = self.state.blob_gateway_application_id().await {
            // TODO: register application logo to blob gateway
        }
    }

    async fn create_liquidity_pool(&mut self) {
        let Some(swap_application_id) = self.state.swap_application_id().await else {
            return;
        };
        let Some(liquidity) = self.state.initial_liquidity().await else {
            return;
        };
        if liquidity.fungible_amount <= Amount::ZERO || liquidity.native_amount <= Amount::ZERO {
            return;
        }

        let call = SwapOperation::AddLiquidity {
            token_0: self.runtime.application_id().forget_abi(),
            token_1: None,
            amount_0_desired: liquidity.fungible_amount,
            amount_1_desired: liquidity.native_amount,
            amount_0_min: liquidity.fungible_amount,
            amount_1_min: liquidity.native_amount,
            // Only for creator to initialize pool
            virtual_liquidity: Some(self.state.virtual_initial_liquidity().await),
            // TODO: let meme creator set their beneficiary
            to: None,
            deadline: None,
        };
        let _ =
            self.runtime
                .call_application(true, swap_application_id.with_abi::<SwapAbi>(), &call);
    }

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

    fn operation_executable(&mut self, operation: &MemeOperation) -> bool {
        match operation {
            MemeOperation::Mine { .. } => {
                self.runtime.chain_id() == self.runtime.application_id().creation.chain_id
            }
            MemeOperation::TransferOwnership { .. } => true,
            _ => self.runtime.chain_id() != self.runtime.application_id().creation.chain_id,
        }
    }

    fn on_op_transfer(
        &mut self,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        self.runtime
            .prepare_message(MemeMessage::Transfer { to, amount })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
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
        rfq_application: Option<Account>,
    ) -> Result<MemeResponse, MemeError> {
        if AccountOwner::User(self.runtime.authenticated_signer().unwrap()) == spender {
            return Err(MemeError::InvalidOwner);
        }
        self.runtime
            .prepare_message(MemeMessage::Approve {
                spender,
                amount,
                rfq_application,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_ownership(&mut self, owner: Owner) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    fn on_op_mine(&mut self, nonce: CryptoHash) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    async fn on_msg_transfer(&mut self, to: AccountOwner, amount: Amount) -> Result<(), MemeError> {
        let from = AccountOwner::User(self.runtime.authenticated_signer().unwrap());
        self.state.transfer(from, to, amount).await
    }

    fn on_msg_transfer_from(
        &mut self,
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<(), MemeError> {
        Ok(())
    }

    async fn formalize_approve_owner(&mut self, amount: Amount) -> Result<AccountOwner, MemeError> {
        let owner = AccountOwner::User(self.runtime.authenticated_signer().unwrap());
        let balance = self.state.balance_of(owner).await;
        if balance >= amount {
            return Ok(owner);
        }

        let meme_owner = AccountOwner::User(self.state.owner().await);
        // Normal user must approve from their own balance
        if owner != meme_owner {
            return Err(MemeError::InvalidOwner);
        }

        if let Some(caller_application_id) = self.runtime.authenticated_caller_id() {
            if let Some(swap_application_id) = self.state.swap_application_id().await {
                // If call from meme owner, and swap application, then approve from application
                // balance
                if caller_application_id != swap_application_id {
                    return Err(MemeError::InvalidOwner);
                }

                let owner = AccountOwner::Application(self.runtime.application_id().forget_abi());
                let balance = self.state.balance_of(owner).await;
                if balance >= amount {
                    return Ok(owner);
                }
            }
        }

        return Err(MemeError::InvalidOwner);
    }

    fn notify_rfq_chain_approved(&mut self, rfq_application: Account) {
        let AccountOwner::Application(application_id) = rfq_application.owner.unwrap() else {
            todo!()
        };
        self.runtime
            .prepare_message(MemeMessage::Approved {
                rfq_application: application_id,
            })
            .with_authentication()
            .send_to(rfq_application.chain_id);
    }

    fn notify_rfq_chain_rejected(&mut self, rfq_application: Account) {
        let AccountOwner::Application(application_id) = rfq_application.owner.unwrap() else {
            todo!()
        };
        self.runtime
            .prepare_message(MemeMessage::Rejected {
                rfq_application: application_id,
            })
            .with_authentication()
            .send_to(rfq_application.chain_id);
    }

    async fn on_msg_approve(
        &mut self,
        spender: AccountOwner,
        amount: Amount,
        rfq_application: Option<Account>,
    ) -> Result<(), MemeError> {
        // Normally user will approve from their own balance
        // Meme creator can approve from their own balance or application balance
        let Ok(owner) = self.formalize_approve_owner(amount).await else {
            if rfq_application.is_some() {
                self.notify_rfq_chain_rejected(rfq_application.unwrap());
            }
            return Ok(());
        };

        // No matter we can or not fulfill the request, we always need to notity rfq chain
        let rc = self.state.approve(owner, spender, amount).await;
        let Some(rfq_application) = rfq_application else {
            return rc;
        };

        if rc.is_ok() {
            self.notify_rfq_chain_approved(rfq_application)
        } else {
            self.notify_rfq_chain_rejected(rfq_application)
        }
        Ok(())
    }

    fn on_msg_approved(&mut self, rfq_application: ApplicationId) -> Result<(), MemeError> {
        // Run on rfq chain
        // TODO: call approved to rfq_application
        Ok(())
    }

    fn on_msg_rejected(&mut self, rfq_application: ApplicationId) -> Result<(), MemeError> {
        // Run on rfq chain
        // TODO: call rejected to rfq_application
        Ok(())
    }

    fn on_msg_transfer_ownership(&mut self, owner: Owner) -> Result<(), MemeError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use abi::{
        meme::{
            InstantiationArgument, Liquidity, Meme, MemeAbi, MemeMessage, MemeOperation,
            MemeParameters, MemeResponse, Metadata,
        },
        store_type::StoreType,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, Owner, TestString},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{MemeContract, MemeState};

    #[tokio::test(flavor = "multi_thread")]
    async fn creation_chain_operation() {
        let mut meme = create_and_instantiate_meme().await;

        let response = meme
            .execute_operation(MemeOperation::Mine {
                nonce: CryptoHash::new(&TestString::new("aaaa")),
            })
            .now_or_never()
            .expect("Execution of meme operation should not await anything");

        assert!(matches!(response, MemeResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    #[should_panic(expected = "Operations must be run on right chain")]
    async fn user_chain_operation() {
        let mut meme = create_and_instantiate_meme().await;
        let to = AccountOwner::User(
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03")
                .unwrap(),
        );

        let response = meme
            .execute_operation(MemeOperation::Transfer {
                to,
                amount: Amount::from_tokens(1),
            })
            .now_or_never()
            .expect("Execution of meme operation should not await anything");

        assert!(matches!(response, MemeResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_transfer() {
        let mut meme = create_and_instantiate_meme().await;
        let from = AccountOwner::User(meme.runtime.authenticated_signer().unwrap());
        let amount = Amount::from_tokens(1);

        let to = AccountOwner::User(
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                .unwrap(),
        );

        meme.state.initialize_balance(from, amount).await.unwrap();

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        meme.execute_message(MemeMessage::Transfer { to, amount })
            .await;

        assert_eq!(meme.state.balances.contains_key(&to).await.unwrap(), true);
        let balance = meme.state.balances.get(&to).await.unwrap().unwrap();
        assert_eq!(balance, amount);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_approve_owner_success() {
        let mut meme = create_and_instantiate_meme().await;
        let from = AccountOwner::User(meme.runtime.authenticated_signer().unwrap());

        let amount = Amount::from_tokens(100);
        let allowance = Amount::from_tokens(22);

        let spender = AccountOwner::User(
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                .unwrap(),
        );

        meme.state.initialize_balance(from, amount).await.unwrap();

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        meme.execute_message(MemeMessage::Approve {
            spender,
            amount: allowance,
            rfq_application: None,
        })
        .await;

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            true
        );
        assert_eq!(
            meme.state
                .allowances
                .get(&from)
                .await
                .unwrap()
                .unwrap()
                .contains_key(&spender),
            true
        );
        let balance = *meme
            .state
            .allowances
            .get(&from)
            .await
            .unwrap()
            .unwrap()
            .get(&spender)
            .unwrap();
        assert_eq!(balance, allowance);

        meme.execute_message(MemeMessage::Approve {
            spender,
            amount: allowance,
            rfq_application: None,
        })
        .await;

        let balance = *meme
            .state
            .allowances
            .get(&from)
            .await
            .unwrap()
            .unwrap()
            .get(&spender)
            .unwrap();
        assert_eq!(balance, allowance.try_mul(2).unwrap());
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_approve_holder_success() {
        let mut meme = create_and_instantiate_meme().await;
        let from = AccountOwner::Application(meme.runtime.application_id().forget_abi());
        let allowance = Amount::from_tokens(10000);

        let spender = AccountOwner::User(
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                .unwrap(),
        );

        meme.execute_message(MemeMessage::Approve {
            spender,
            amount: allowance,
            rfq_application: None,
        })
        .await;

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            true
        );
        assert_eq!(
            meme.state
                .allowances
                .get(&from)
                .await
                .unwrap()
                .unwrap()
                .contains_key(&spender),
            true
        );
        let balance = *meme
            .state
            .allowances
            .get(&from)
            .await
            .unwrap()
            .unwrap()
            .get(&spender)
            .unwrap();
        assert_eq!(balance, allowance);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_approve_insufficient_balance() {
        let mut meme = create_and_instantiate_meme().await;
        let from = AccountOwner::User(meme.runtime.authenticated_signer().unwrap());

        let amount = Amount::from_tokens(100);
        let allowance = Amount::from_tokens(220);

        let spender = AccountOwner::User(
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                .unwrap(),
        );

        meme.state.initialize_balance(from, amount).await.unwrap();

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        // It won't panic here, it'll approved from application balance
        meme.execute_message(MemeMessage::Approve {
            spender,
            amount: allowance,
            rfq_application: None,
        })
        .await;

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            false
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[should_panic(expected = "Failed MSG: approve: InvalidOwner")]
    async fn message_approve_meme_owner_self_insufficient_balance() {
        let mut meme = create_and_instantiate_meme().await;
        let from = AccountOwner::User(meme.runtime.authenticated_signer().unwrap());

        let amount = Amount::from_tokens(100);
        let allowance = Amount::from_tokens(220);

        meme.state.initialize_balance(from, amount).await.unwrap();

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        // It won't panic here, it'll approved from application balance
        meme.execute_message(MemeMessage::Approve {
            spender: from,
            amount: allowance,
            rfq_application: None,
        })
        .await;

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            false
        );
        assert_eq!(
            meme.state
                .allowances
                .get(&from)
                .await
                .unwrap()
                .unwrap()
                .contains_key(&from),
            false
        );
    }

    #[test]
    fn cross_application_call() {}

    fn mock_application_call(
        _authenticated: bool,
        _application_id: ApplicationId,
        _operation: Vec<u8>,
    ) -> Vec<u8> {
        vec![0]
    }

    async fn create_and_instantiate_meme() -> MemeContract {
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
        let application = AccountOwner::Application(application_id.forget_abi());

        let swap_application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000002";
        let swap_application_id = ApplicationId::from_str(swap_application_id_str).unwrap();

        let runtime = ContractRuntime::new()
            .with_application_parameters(MemeParameters {})
            .with_can_change_application_permissions(true)
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_owner_balance(application, Amount::ZERO)
            .with_authenticated_caller_id(swap_application_id)
            .with_call_application_handler(mock_application_call)
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
            initial_liquidity: Some(Liquidity {
                fungible_amount: Amount::from_tokens(10000000),
                native_amount: Amount::from_tokens(10),
            }),
            blob_gateway_application_id: None,
            ams_application_id: None,
            proxy_application_id: None,
            swap_application_id: Some(swap_application_id),
            virtual_initial_liquidity: true,
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
            contract
                .state
                .balances
                .contains_key(&application)
                .await
                .unwrap(),
            true
        );
        assert_eq!(
            contract
                .state
                .balances
                .get(&application)
                .await
                .as_ref()
                .unwrap()
                .unwrap(),
            instantiation_argument.meme.initial_supply
        );

        contract
    }
}
