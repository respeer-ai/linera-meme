// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::swap::{
    liquidity_rfq::{LiquidityRfqAbi, LiquidityRfqParameters},
    router::{InstantiationArgument, SwapAbi, SwapMessage, SwapOperation, SwapResponse},
};
use linera_sdk::{
    base::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, BytecodeId, ChainId,
        MessageId, Timestamp, WithContractAbi,
    },
    views::{RootView, View},
    Contract, ContractRuntime,
};
use swap::SwapError;

use self::state::SwapState;

pub struct SwapContract {
    state: SwapState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(SwapContract);

impl WithContractAbi for SwapContract {
    type Abi = SwapAbi;
}

impl Contract for SwapContract {
    type Message = SwapMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        SwapContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.instantiate(argument).await;
    }

    async fn execute_operation(&mut self, operation: SwapOperation) -> SwapResponse {
        match operation {
            SwapOperation::AddLiquidity {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
                deadline,
            } => self
                .on_op_add_liquidity(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    virtual_liquidity,
                    to,
                    deadline,
                )
                .await
                .expect("Failed OP: add liquidity"),
            SwapOperation::LiquidityFundApproved {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
                deadline,
            } => self
                .on_op_liquidity_fund_approved(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    // Only for creator to initialize pool
                    virtual_liquidity,
                    to,
                    deadline,
                )
                .expect("Failed OP: liquidity fund approved"),
            SwapOperation::RemoveLiquidity {
                token_0,
                token_1,
                liquidity,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_op_remove_liquidity(
                    token_0,
                    token_1,
                    liquidity,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .expect("Failed OP: remove liquidity"),
            SwapOperation::Swap {
                token_0,
                token_1,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                deadline,
            } => self
                .on_op_swap(
                    token_0,
                    token_1,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    deadline,
                )
                .expect("Failed OP: swap"),
        }
    }

    async fn execute_message(&mut self, message: SwapMessage) {
        // All messages must be run on creation chain side
        if self.runtime.chain_id() != self.runtime.application_id().creation.chain_id {
            panic!("Messages must only be run on creation chain");
        }

        match message {
            SwapMessage::CreateRfq { rfq_bytecode_id } => self
                .on_msg_create_rfq(rfq_bytecode_id)
                .expect("Failed MSG: create rfq"),
            SwapMessage::LiquidityFundApproved {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
                deadline,
            } => self
                .on_msg_liquidity_fund_approved(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    // Only for creator to initialize pool
                    virtual_liquidity,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: liquidity fund approved"),
            SwapMessage::RemoveLiquidity {
                token_0,
                token_1,
                liquidity,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_msg_remove_liquidity(
                    token_0,
                    token_1,
                    liquidity,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: remove liquidity"),
            SwapMessage::Swap {
                token_0,
                token_1,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                deadline,
            } => self
                .on_msg_swap(
                    token_0,
                    token_1,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: swap"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl SwapContract {
    fn formalize_virtual_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        virtual_liquidity: Option<bool>,
    ) -> bool {
        let Some(virtual_liquidity) = virtual_liquidity else {
            return false;
        };
        if !virtual_liquidity {
            return false;
        }
        if token_1.is_none() {
            return false;
        }

        let Some(caller_application_id) = self.runtime.authenticated_caller_id() else {
            return false;
        };
        if caller_application_id != token_0 {
            return false;
        }
        if self.runtime.chain_id() != token_0.creation.chain_id {
            return false;
        }
        return true;
    }

    fn create_rfq_chain(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<(MessageId, ChainId), SwapError> {
        // It should allow router and meme applications
        let ownership = self.runtime.chain_ownership();

        let router_application_id = self.runtime.application_id().forget_abi();
        let mut application_ids = vec![token_0, router_application_id];
        if let Some(token_1) = token_1 {
            application_ids.push(token_1);
        }

        let permissions = ApplicationPermissions {
            execute_operations: Some(application_ids),
            mandatory_applications: vec![],
            close_chain: vec![router_application_id],
            change_application_permissions: vec![router_application_id],
        };
        Ok(self
            .runtime
            .open_chain(ownership, permissions, Amount::from_tokens(1)))
    }

    async fn request_liquidity_funds(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<(), SwapError> {
        // 1: Create rfq chain
        let (message_id, chain_id) = self.create_rfq_chain(token_0, token_1)?;
        // 2: Create rfq application
        let bytecode_id = self.state.liquidity_rfq_bytecode_id().await;

        self.runtime
            .prepare_message(SwapMessage::CreateRfq {
                rfq_bytecode_id: bytecode_id,
            })
            .with_authentication()
            .send_to(chain_id);

        Ok(())
    }

    async fn on_op_add_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: Option<bool>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        let virtual_liquidity =
            self.formalize_virtual_liquidity(token_0, token_1, virtual_liquidity);

        // Request liquidity funds in rfq chain
        // If success, rfq application will call LiquidityFundApproved then we can create pool or
        // add liquidity
        // TODO: it may should be run on creation chain to use swap's owners
        self.request_liquidity_funds(token_0, token_1).await?;

        Ok(SwapResponse::Ok)
    }

    fn on_op_liquidity_fund_approved(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn on_op_remove_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn on_op_swap(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn pool_chain_add_liquidity(
        &mut self,
        pool_application: Account,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // 1: Call pool application to add liquidity
        Ok(())
    }

    // Pool application is run on its own chain
    fn create_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // 1: Create pool chain
        // 2: Create pool application with initial liquidity
        Ok(())
    }

    fn on_msg_create_rfq(&mut self, rfq_bytecode_id: BytecodeId) -> Result<(), SwapError> {
        // Run on rfq chain

        let _ = self
            .runtime
            .create_application::<LiquidityRfqAbi, LiquidityRfqParameters, ()>(
                rfq_bytecode_id,
                &LiquidityRfqParameters {},
                &(),
                vec![],
            );

        Ok(())
    }

    async fn on_msg_liquidity_fund_approved(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // Fund is ready, create liquidity pool
        if let Some(pool) = self.state.get_pool_exchangable(token_0, token_1).await? {
            self.pool_chain_add_liquidity(
                pool.pool_application,
                if pool.token_0 == token_0 {
                    amount_0_desired
                } else {
                    amount_1_desired
                },
                if pool.token_0 == token_0 {
                    amount_1_desired
                } else {
                    amount_0_desired
                },
                if pool.token_0 == token_0 {
                    amount_0_min
                } else {
                    amount_1_min
                },
                if pool.token_0 == token_0 {
                    amount_1_min
                } else {
                    amount_0_min
                },
                to,
                deadline,
            )
        } else {
            self.create_pool(
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
                deadline,
            )
        }
    }

    async fn on_msg_remove_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        Ok(())
    }

    async fn on_msg_swap(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::router::{InstantiationArgument, SwapAbi, SwapOperation, SwapResponse};
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{
            Amount, ApplicationId, ApplicationPermissions, BytecodeId, ChainOwnership, MessageId,
            Owner,
        },
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{SwapContract, SwapState};

    #[test]
    fn operation_meme_native() {
        let mut swap = create_and_instantiate_swap();

        let meme_1_id = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let response = swap
            .execute_operation(SwapOperation::AddLiquidity {
                token_0: meme_1,
                token_1: None,
                amount_0_desired: Amount::ONE,
                amount_1_desired: Amount::ONE,
                amount_0_min: Amount::ONE,
                amount_1_min: Amount::ONE,
                virtual_liquidity: Some(false),
                to: None,
                deadline: None,
            })
            .now_or_never()
            .expect("Execution of swap operation should not await anything");

        assert!(matches!(response, SwapResponse::Ok));
    }

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_swap() -> SwapContract {
        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000008";
        let application_id = ApplicationId::from_str(application_id_str)
            .unwrap()
            .with_abi::<SwapAbi>();
        let mut runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_application_id(application_id)
            .with_chain_ownership(ChainOwnership::single(owner));

        let message_id = MessageId::from_str("dad01517c7a3c428ea903253a9e59964e8db06d323a9bd3f4c74d6366832bdbf801200000000000000000000").unwrap();
        let meme_1_id = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let permissions = ApplicationPermissions {
            execute_operations: Some(vec![meme_1, application_id.forget_abi()]),
            mandatory_applications: vec![],
            close_chain: vec![application_id.forget_abi()],
            change_application_permissions: vec![application_id.forget_abi()],
        };

        runtime.add_expected_open_chain_call(
            ChainOwnership::single(owner),
            permissions,
            Amount::from_tokens(1),
            message_id,
        );

        let mut contract = SwapContract {
            state: SwapState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let bytecode_id = BytecodeId::from_str("58cc6e264a19cddf027010db262ca56a18e7b63e2a7ad1561ea9841f9aef308fc5ae59261c0137891a342001d3d4446a26c3666ed81aadf7e5eec6a01c86db6d").unwrap();
        contract
            .instantiate(InstantiationArgument {
                liquidity_rfq_bytecode_id: bytecode_id,
            })
            .now_or_never()
            .expect("Initialization of swap state should not await anything");

        assert_eq!(
            *contract
                .state
                .liquidity_rfq_bytecode_id
                .get()
                .as_ref()
                .unwrap(),
            bytecode_id,
        );

        contract
    }
}
