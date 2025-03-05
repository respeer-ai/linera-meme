// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{
        InstantiationArgument, MemeAbi, MemeMessage, MemeOperation, MemeParameters, MemeResponse,
    },
    proxy::{ProxyAbi, ProxyOperation},
    swap::router::{SwapAbi, SwapOperation},
};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ApplicationPermissions, CryptoHash, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme::MemeError;

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

        let owner = self.owner_account();
        let application = self.application_account();

        self.state
            .instantiate(owner, application, instantiation_argument)
            .await
            .expect("Failed instantiate");

        // Let owner hold one hundred tokens for easy test
        self.state
            .initialize_balance(owner, self.state.initial_owner_balance().await)
            .await
            .expect("Failed initialize balance");

        self.register_application().await;
        self.register_logo().await;

        // When the meme application is created, initial liquidity allowance should already be approved
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
            MemeOperation::Approve { spender, amount } => self
                .on_op_approve(spender, amount)
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
            MemeMessage::Transfer { from, to, amount } => self
                .on_msg_transfer(from, to, amount)
                .await
                .expect("Failed MSG: transfer"),
            MemeMessage::TransferFrom {
                owner,
                from,
                to,
                amount,
            } => self
                .on_msg_transfer_from(owner, from, to, amount)
                .await
                .expect("Failed MSG: trasnfer from"),
            MemeMessage::Approve {
                owner,
                spender,
                amount,
            } => self
                .on_msg_approve(owner, spender, amount)
                .await
                .expect("Failed MSG: approve"),
            MemeMessage::TransferOwnership { owner, new_owner } => self
                .on_msg_transfer_ownership(owner, new_owner)
                .await
                .expect("Failed MSG: transfer ownership"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl MemeContract {
    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => Some(AccountOwner::User(owner)),
                _ => None,
            },
        }
    }

    fn application_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: Some(AccountOwner::Application(
                self.runtime.application_id().forget_abi(),
            )),
        }
    }

    fn caller_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_caller_id() {
                Some(application_id) => Some(AccountOwner::Application(application_id)),
                _ => None,
            },
        }
    }

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
        let virtual_liquidity = self.state.virtual_initial_liquidity().await;

        let call = SwapOperation::InitializeLiquidity {
            token_0: self.runtime.application_id().forget_abi(),
            amount_0: liquidity.fungible_amount,
            amount_1: liquidity.native_amount,
            virtual_liquidity,
            to: None,
        };
        let _ =
            self.runtime
                .call_application(true, swap_application_id.with_abi::<SwapAbi>(), &call);
    }

    fn operation_executable(&mut self, operation: &MemeOperation) -> bool {
        match operation {
            MemeOperation::Mine { .. } => {
                self.runtime.chain_id() == self.runtime.application_id().creation.chain_id
            }
            _ => true,
        }
    }

    fn on_op_transfer(&mut self, to: Account, amount: Amount) -> Result<MemeResponse, MemeError> {
        let from = self.owner_account();
        self.runtime
            .prepare_message(MemeMessage::Transfer { from, to, amount })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_from(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(MemeMessage::TransferFrom {
                owner,
                from,
                to,
                amount,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(MemeResponse::Ok)
    }

    fn on_op_approve(
        &mut self,
        spender: Account,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        let owner = self.owner_account();
        if owner == spender {
            return Err(MemeError::InvalidOwner);
        }
        self.runtime
            .prepare_message(MemeMessage::Approve {
                owner,
                spender,
                amount,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_ownership(&mut self, new_owner: Account) -> Result<MemeResponse, MemeError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(MemeMessage::TransferOwnership { owner, new_owner })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(MemeResponse::Ok)
    }

    fn on_op_mine(&mut self, nonce: CryptoHash) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    async fn on_msg_transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), MemeError> {
        self.state.transfer(from, to, amount).await
    }

    async fn on_msg_transfer_from(
        &mut self,
        owner: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), MemeError> {
        self.state.transfer_from(owner, from, to, amount).await
    }

    async fn on_msg_approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), MemeError> {
        let balance = self.state.balance_of(owner).await;
        assert!(amount <= balance, "Insufficient balance");

        self.state.approve(owner, spender, amount).await
    }

    async fn on_msg_transfer_ownership(
        &mut self,
        owner: Account,
        new_owner: Account,
    ) -> Result<(), MemeError> {
        self.state.transfer_ownership(owner, new_owner).await
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
        base::{
            Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, Owner, TestString,
        },
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
    async fn user_chain_operation() {
        let mut meme = create_and_instantiate_meme().await;
        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03")
                    .unwrap(),
            )),
        };

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
        let from = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };
        let amount = meme.state.initial_owner_balance().await;

        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                    .unwrap(),
            )),
        };

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        meme.execute_message(MemeMessage::Transfer { from, to, amount })
            .await;

        assert_eq!(meme.state.balances.contains_key(&to).await.unwrap(), true);
        let balance = meme.state.balances.get(&to).await.unwrap().unwrap();
        assert_eq!(balance, amount);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[should_panic(expected = "Insufficient balance")]
    async fn message_transfer_insufficient_funds() {
        let mut meme = create_and_instantiate_meme().await;
        let from = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };
        let amount = meme.state.initial_owner_balance().await;
        let transfer_amount = amount.try_add(Amount::ONE).unwrap();

        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                    .unwrap(),
            )),
        };

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        meme.execute_message(MemeMessage::Transfer {
            from,
            to,
            amount: transfer_amount,
        })
        .await;

        assert_eq!(meme.state.balances.contains_key(&to).await.unwrap(), true);
        let balance = meme.state.balances.get(&to).await.unwrap().unwrap();
        assert_eq!(balance, amount);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_approve_owner_success() {
        let mut meme = create_and_instantiate_meme().await;
        let from = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };

        let amount = meme.state.initial_owner_balance().await;
        let allowance = Amount::from_tokens(22);

        let spender = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                    .unwrap(),
            )),
        };

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        meme.execute_message(MemeMessage::Approve {
            owner: from,
            spender,
            amount: allowance,
        })
        .await;

        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount.try_sub(allowance).unwrap());

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
            owner: from,
            spender,
            amount: allowance,
        })
        .await;

        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(
            balance,
            amount
                .try_sub(allowance)
                .unwrap()
                .try_sub(allowance)
                .unwrap()
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
        assert_eq!(balance, allowance.try_mul(2).unwrap());

        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08")
                    .unwrap(),
            )),
        };

        meme.execute_message(MemeMessage::TransferFrom {
            owner: spender,
            from,
            to,
            amount: allowance,
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
        assert_eq!(balance, allowance);

        let balance = meme.state.balances.get(&to).await.unwrap().unwrap();
        assert_eq!(balance, allowance);
    }

    #[tokio::test(flavor = "multi_thread")]
    #[should_panic(expected = "Insufficient balance")]
    async fn message_approve_insufficient_balance() {
        let mut meme = create_and_instantiate_meme().await;
        let from = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };

        let amount = meme.state.initial_owner_balance().await;
        let allowance = Amount::from_tokens(220);

        let spender = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                    .unwrap(),
            )),
        };

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        // It won't panic here, it'll approved from application balance
        meme.execute_message(MemeMessage::Approve {
            owner: from,
            spender,
            amount: allowance,
        })
        .await;

        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            false
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    #[should_panic(expected = "Insufficient balance")]
    async fn message_approve_meme_owner_self_insufficient_balance() {
        let mut meme = create_and_instantiate_meme().await;
        let from = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };

        let amount = meme.state.initial_owner_balance().await;
        let allowance = Amount::from_tokens(220);

        assert_eq!(meme.state.balances.contains_key(&from).await.unwrap(), true);
        let balance = meme.state.balances.get(&from).await.unwrap().unwrap();
        assert_eq!(balance, amount);

        // It won't panic here, it'll approved from application balance
        meme.execute_message(MemeMessage::Approve {
            owner: from,
            spender: from,
            amount: allowance,
        })
        .await;

        assert_eq!(
            meme.state.allowances.contains_key(&from).await.unwrap(),
            false
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_transfer_ownership() {
        let mut meme = create_and_instantiate_meme().await;
        let owner = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                meme.runtime.authenticated_signer().unwrap(),
            )),
        };
        let new_owner = Account {
            chain_id: meme.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01")
                    .unwrap(),
            )),
        };

        // It won't panic here, it'll approved from application balance
        meme.execute_message(MemeMessage::TransferOwnership { owner, new_owner })
            .await;

        assert_eq!(meme.state.owner.get().unwrap(), new_owner);
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
        let application = Account {
            chain_id,
            owner: Some(AccountOwner::Application(application_id.forget_abi())),
        };

        let swap_application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000002";
        let swap_application_id = ApplicationId::from_str(swap_application_id_str).unwrap();
        let swap_application = Account {
            chain_id,
            owner: Some(AccountOwner::Application(swap_application_id)),
        };

        let runtime = ContractRuntime::new()
            .with_application_parameters(MemeParameters {})
            .with_can_change_application_permissions(true)
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_owner_balance(
                AccountOwner::Application(application_id.forget_abi()),
                Amount::ZERO,
            )
            .with_authenticated_caller_id(swap_application_id)
            .with_call_application_handler(mock_application_call)
            .with_authenticated_signer(operator);
        let mut contract = MemeContract {
            state: MemeState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let initial_supply = Amount::from_tokens(21000000);
        let swap_allowance = Amount::from_tokens(10000000);
        let instantiation_argument = InstantiationArgument {
            meme: Meme {
                name: "Test Token".to_string(),
                ticker: "LTT".to_string(),
                decimals: 6,
                initial_supply,
                total_supply: initial_supply,
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
                fungible_amount: swap_allowance,
                native_amount: Amount::from_tokens(10),
            }),
            blob_gateway_application_id: None,
            ams_application_id: None,
            proxy_application_id: None,
            swap_application_id: Some(swap_application_id),
            virtual_initial_liquidity: true,
        };

        contract.instantiate(instantiation_argument.clone()).await;
        let application_balance = initial_supply
            .try_sub(swap_allowance)
            .unwrap()
            .try_sub(contract.state.initial_owner_balance().await)
            .unwrap();

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
            application_balance,
        );
        assert_eq!(
            contract
                .state
                .allowances
                .contains_key(&application)
                .await
                .unwrap(),
            true
        );
        assert_eq!(
            contract
                .state
                .allowances
                .get(&application)
                .await
                .unwrap()
                .unwrap()
                .contains_key(&swap_application),
            true
        );
        assert_eq!(
            *contract
                .state
                .allowances
                .get(&application)
                .await
                .unwrap()
                .unwrap()
                .get(&swap_application)
                .unwrap(),
            swap_allowance
        );

        contract
    }
}
