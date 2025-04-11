// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    ams::{AmsAbi, AmsOperation, Metadata, MEME},
    blob_gateway::{BlobDataType, BlobGatewayAbi, BlobGatewayOperation},
    meme::{
        InstantiationArgument, Liquidity, MemeAbi, MemeMessage, MemeOperation, MemeParameters,
        MemeResponse,
    },
    policy::open_chain_fee_budget,
    swap::router::{SwapAbi, SwapOperation},
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ChainId, CryptoHash, WithContractAbi},
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
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeContract { state, runtime }
    }

    async fn instantiate(&mut self, mut instantiation_argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        let signer = self.runtime.authenticated_signer().unwrap();
        // Signer should be the same as the creator
        assert!(self.creator_signer() == signer, "Invalid owner");

        let creator = self.creator();
        let application = self.application_account();

        instantiation_argument.meme.virtual_initial_liquidity = self.virtual_initial_liquidity();
        instantiation_argument.meme.initial_liquidity = self.initial_liquidity();

        self.state
            .instantiate(creator, application, instantiation_argument)
            .await
            .expect("Failed instantiate");

        // Let creator hold one hundred tokens for easy test
        self.state
            .initialize_balance(creator, self.state.initial_owner_balance().await)
            .await
            .expect("Failed initialize balance");

        if let Some(liquidity) = self.initial_liquidity() {
            let swap_creator_chain = self.swap_creator_chain_id();
            self.state
                .initialize_liquidity(liquidity, swap_creator_chain)
                .await
                .expect("Failed initialize liquidity");
        }

        self.register_application().await;
        self.register_logo().await;

        // When the meme application is created, initial liquidity allowance should already be approved
        self.create_liquidity_pool()
            .await
            .expect("Failed create liquidity pool");
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
            MemeOperation::TransferFromApplication { to, amount } => self
                .on_op_transfer_from_application(to, amount)
                .await
                .expect("Failed OP: trasnfer from application"),
            MemeOperation::InitializeLiquidity { to, amount } => self
                .on_op_initialize_liquidity(to, amount)
                .await
                .expect("Failed OP: initialize liquidity"),
            MemeOperation::Approve { spender, amount } => self
                .on_op_approve(spender, amount)
                .expect("Failed OP: approve"),
            MemeOperation::TransferOwnership { new_owner } => self
                .on_op_transfer_ownership(new_owner)
                .expect("Failed OP: transfer ownership"),
            MemeOperation::TransferToCaller { amount } => self
                .on_op_transfer_to_caller(amount)
                .await
                .expect("Failed OP: transfer to caller"),
            MemeOperation::Mine { nonce } => self.on_op_mine(nonce).expect("Failed OP: mine"),
        }
    }

    async fn execute_message(&mut self, message: MemeMessage) {
        // All messages must be run on creation chain side
        if self.runtime.chain_id() != self.runtime.application_creator_chain_id() {
            panic!("Messages must only be run on creation chain");
        }

        match message {
            MemeMessage::LiquidityFunded => self
                .on_msg_liquidity_funded()
                .await
                .expect("Failed MSG: liquidity funded"),
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
            MemeMessage::TransferFromApplication { caller, to, amount } => self
                .on_msg_transfer_from_application(caller, to, amount)
                .await
                .expect("Failed OP: trasnfer from application"),
            MemeMessage::InitializeLiquidity { caller, to, amount } => self
                .on_msg_initialize_liquidity(caller, to, amount)
                .await
                .expect("Failed OP: initialize liquidity"),
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
    fn creator(&mut self) -> Account {
        self.runtime.application_parameters().creator
    }

    fn creator_signer(&mut self) -> AccountOwner {
        self.creator().owner
    }

    fn virtual_initial_liquidity(&mut self) -> bool {
        self.runtime
            .application_parameters()
            .virtual_initial_liquidity
    }

    fn initial_liquidity(&mut self) -> Option<Liquidity> {
        self.runtime.application_parameters().initial_liquidity
    }

    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => owner,
                _ => AccountOwner::CHAIN,
            },
        }
    }

    fn application_creation_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.application_creator_chain_id(),
            owner: AccountOwner::from(self.runtime.application_id().forget_abi()),
        }
    }

    fn application_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: AccountOwner::from(self.runtime.application_id().forget_abi()),
        }
    }

    fn message_caller_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.message_id().unwrap().chain_id,
            owner: AccountOwner::from(self.runtime.authenticated_caller_id().unwrap()),
        }
    }

    fn message_owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.message_id().unwrap().chain_id,
            owner: self.runtime.authenticated_signer().unwrap(),
        }
    }

    async fn register_application(&mut self) {
        if let Some(ams_application_id) = self.state.ams_application_id() {
            let call = AmsOperation::Register {
                metadata: Metadata {
                    creator: self.creator(),
                    application_name: self.state.name(),
                    application_id: self.runtime.application_id().forget_abi(),
                    application_type: MEME.to_string(),
                    key_words: vec![
                        "Linera".to_string(),
                        "Meme".to_string(),
                        "PoW microchain".to_string(),
                    ],
                    logo_store_type: self.state.logo_store_type(),
                    logo: self.state.logo(),
                    description: self.state.description(),
                    twitter: self.state.twitter(),
                    telegram: self.state.telegram(),
                    discord: self.state.discord(),
                    website: self.state.website(),
                    github: self.state.github(),
                    spec: Some(
                        serde_json::to_string(&self.state.meme()).expect("Failed serialize meme"),
                    ),
                    created_at: self.runtime.system_time(),
                },
            };
            let _ =
                self.runtime
                    .call_application(true, ams_application_id.with_abi::<AmsAbi>(), &call);
        }
    }

    fn swap_creator_chain_id(&mut self) -> ChainId {
        self.runtime.application_parameters().swap_creator_chain_id
    }

    async fn register_logo(&mut self) {
        if let Some(blob_gateway_application_id) = self.state.blob_gateway_application_id() {
            let call = BlobGatewayOperation::Register {
                store_type: self.state.logo_store_type(),
                data_type: BlobDataType::Image,
                blob_hash: self.state.logo(),
            };
            let _ = self.runtime.call_application(
                true,
                blob_gateway_application_id.with_abi::<BlobGatewayAbi>(),
                &call,
            );
        }
    }

    fn fund_account(&mut self, to: Account, amount: Amount) {
        assert!(amount > Amount::ZERO, "Invalid fund amount");

        let signer = self.runtime.authenticated_signer().unwrap();
        let ownership = self.runtime.chain_ownership();
        // If we're not chain owner, we cannot transfer chain balance
        let can_from_chain = ownership.all_owners().any(|&owner| owner == signer);

        let owner_balance = self.runtime.owner_balance(signer);
        let chain_balance = self.runtime.chain_balance();

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount <= owner_balance || !can_from_chain {
            Amount::ZERO
        } else {
            amount.try_sub(owner_balance).expect("Invalid amount")
        };

        assert!(from_owner_balance <= owner_balance, "Insufficient balance");
        assert!(from_chain_balance <= chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime.transfer(signer, to, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime
                .transfer(AccountOwner::CHAIN, to, from_chain_balance);
        }
    }

    async fn create_liquidity_pool(&mut self) -> Result<(), MemeError> {
        let Some(swap_application_id) = self.state.swap_application_id() else {
            return Ok(());
        };
        let Some(liquidity) = self.initial_liquidity() else {
            return Ok(());
        };
        if liquidity.fungible_amount <= Amount::ZERO || liquidity.native_amount <= Amount::ZERO {
            return Ok(());
        }

        // Meme chain will be created by swap creator chain, so we fund signer on swap creator
        // chain then it'll fund meme chain
        let swap_creator_chain = self.swap_creator_chain_id();
        self.fund_account(
            Account {
                chain_id: swap_creator_chain,
                owner: AccountOwner::CHAIN,
            },
            open_chain_fee_budget(),
        );
        if !self.virtual_initial_liquidity() {
            // At this moment (instantiating) there is no balance on application, so we should transfer from chain
            self.fund_account(
                Account {
                    chain_id: swap_creator_chain,
                    owner: AccountOwner::from(swap_application_id),
                },
                liquidity.native_amount,
            );
        }

        // We fund swap application here but the funds will be process in this block, so we should
        // call swap application in next block
        // TODO: remove after https://github.com/linera-io/linera-protocol/issues/3486 being fixed
        self.runtime
            .prepare_message(MemeMessage::LiquidityFunded)
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());

        Ok(())
    }

    fn operation_executable(&mut self, operation: &MemeOperation) -> bool {
        match operation {
            MemeOperation::Mine { .. } => {
                self.runtime.chain_id() == self.runtime.application_creator_chain_id()
            }
            _ => true,
        }
    }

    fn on_op_transfer(&mut self, to: Account, amount: Amount) -> Result<MemeResponse, MemeError> {
        let from = self.owner_account();
        self.runtime
            .prepare_message(MemeMessage::Transfer { from, to, amount })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
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
            .send_to(self.runtime.application_creator_chain_id());
        Ok(MemeResponse::Ok)
    }

    async fn on_op_transfer_from_application(
        &mut self,
        to: Account,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        // TODO: check called from caller creator chain
        let caller_id = self.runtime.authenticated_caller_id().unwrap();
        // TODO: use creator chain id if we can get it from runtime
        let chain_id = self.runtime.chain_id();

        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        self.runtime
            .prepare_message(MemeMessage::TransferFromApplication { caller, to, amount })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(MemeResponse::Ok)
    }

    async fn on_op_initialize_liquidity(
        &mut self,
        to: Account,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        // TODO: check called from caller creator chain
        let caller_id = self.runtime.authenticated_caller_id().unwrap();
        // TODO: use creator chain id if we can get it from runtime
        let chain_id = self.runtime.chain_id();

        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        self.runtime
            .prepare_message(MemeMessage::InitializeLiquidity { caller, to, amount })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
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
            .send_to(self.runtime.application_creator_chain_id());
        Ok(MemeResponse::Ok)
    }

    fn on_op_transfer_ownership(&mut self, new_owner: Account) -> Result<MemeResponse, MemeError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(MemeMessage::TransferOwnership { owner, new_owner })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(MemeResponse::Ok)
    }

    async fn on_op_transfer_to_caller(
        &mut self,
        amount: Amount,
    ) -> Result<MemeResponse, MemeError> {
        assert!(
            self.runtime.authenticated_caller_id().is_some(),
            "Invalid caller"
        );

        // Should only be called from another application message, so we need to transfer from
        // message creator's owner
        let caller = self.message_caller_account();
        let from = self.message_owner_account();
        match self.state.transfer_ensure(from, caller, amount).await {
            Ok(_) => Ok(MemeResponse::Ok),
            Err(err) => Ok(MemeResponse::Fail(err.to_string())),
        }
    }

    // TODO: check first operation of the block must be mine
    // TODO: distribute reward to block proposer
    fn on_op_mine(&mut self, _nonce: CryptoHash) -> Result<MemeResponse, MemeError> {
        Ok(MemeResponse::Ok)
    }

    async fn on_msg_liquidity_funded(&mut self) -> Result<(), MemeError> {
        let virtual_liquidity = self.virtual_initial_liquidity();
        let Some(liquidity) = self.initial_liquidity() else {
            return Ok(());
        };
        let Some(swap_application_id) = self.state.swap_application_id() else {
            return Ok(());
        };

        let creator = self.creator();
        let call = SwapOperation::InitializeLiquidity {
            creator,
            token_0_creator_chain_id: self.runtime.chain_id(),
            token_0: self.runtime.application_id().forget_abi(),
            amount_0: liquidity.fungible_amount,
            amount_1: liquidity.native_amount,
            virtual_liquidity,
            to: None,
        };
        let _ =
            self.runtime
                .call_application(true, swap_application_id.with_abi::<SwapAbi>(), &call);
        Ok(())
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

    async fn on_msg_transfer_from_application(
        &mut self,
        caller: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), MemeError> {
        self.state.transfer(caller, to, amount).await
    }

    async fn on_msg_initialize_liquidity(
        &mut self,
        caller: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), MemeError> {
        assert!(
            caller.chain_id == self.swap_creator_chain_id(),
            "Invalid caller"
        );
        assert!(
            caller.owner == AccountOwner::from(self.state.swap_application_id().unwrap()),
            "Invalid caller"
        );

        let from = self.application_creation_account();
        self.state.transfer_from(caller, from, to, amount).await
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
        swap::router::SwapResponse,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        bcs,
        linera_base_types::{
            Account, AccountOwner, Amount, ApplicationId, ChainId, ChainOwnership, CryptoHash,
            TestString,
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
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
            )
            .unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
        };
        let amount = meme.state.initial_owner_balance().await;

        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
        };
        let amount = meme.state.initial_owner_balance().await;
        let transfer_amount = amount.try_add(Amount::ONE).unwrap();

        let to = Account {
            chain_id: meme.runtime.chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
        };

        let amount = meme.state.initial_owner_balance().await;
        let allowance = Amount::from_tokens(22);

        let spender = Account {
            chain_id: meme.runtime.chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
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
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
            )
            .unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
        };

        let amount = meme.state.initial_owner_balance().await;
        let allowance = Amount::from_tokens(220);

        let spender = Account {
            chain_id: meme.runtime.chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
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
            owner: meme.runtime.authenticated_signer().unwrap(),
        };
        let new_owner = Account {
            chain_id: meme.runtime.chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
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
        bcs::to_bytes(&SwapResponse::ChainId(
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap(),
        ))
        .unwrap()
    }

    async fn create_and_instantiate_meme() -> MemeContract {
        let operator = AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
        )
        .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let owner = Account {
            chain_id,
            owner: operator,
        };

        let application_id = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap()
        .with_abi::<MemeAbi>();
        let application = Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        };

        let swap_application_id = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap();
        let swap_application = Account {
            chain_id,
            owner: AccountOwner::from(swap_application_id),
        };

        let initial_supply = Amount::from_tokens(21000000);
        let swap_allowance = Amount::from_tokens(10000000);
        let parameters = MemeParameters {
            creator: owner,
            initial_liquidity: Some(Liquidity {
                fungible_amount: swap_allowance,
                native_amount: Amount::from_tokens(10),
            }),
            virtual_initial_liquidity: true,
            swap_creator_chain_id: chain_id,
        };
        let runtime = ContractRuntime::new()
            .with_can_change_application_permissions(true)
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_chain_ownership(ChainOwnership::single(operator))
            .with_owner_balance(
                AccountOwner::from(application_id.forget_abi()),
                Amount::from_tokens(10000),
            )
            .with_owner_balance(operator, Amount::from_tokens(10000))
            .with_owner_balance(AccountOwner::from(swap_application_id), Amount::ZERO)
            .with_chain_balance(Amount::ONE)
            .with_authenticated_caller_id(swap_application_id)
            .with_call_application_handler(mock_application_call)
            .with_application_creator_chain_id(chain_id)
            .with_application_parameters(parameters.clone())
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
                initial_supply,
                total_supply: initial_supply,
                metadata: Metadata {
                    logo_store_type: StoreType::S3,
                    logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                    description: "Test token description".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                    live_stream: None,
                },
                virtual_initial_liquidity: true,
                initial_liquidity: parameters.initial_liquidity,
            },
            blob_gateway_application_id: None,
            ams_application_id: None,
            proxy_application_id: None,
            swap_application_id: Some(swap_application_id),
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
