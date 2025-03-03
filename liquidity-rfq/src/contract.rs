// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{MemeAbi, MemeOperation},
    swap::liquidity_rfq::{
        LiquidityRfqAbi, LiquidityRfqOperation, LiquidityRfqParameters, LiquidityRfqResponse,
    },
};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ApplicationId, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use liquidity_rfq::LiquidityRfqError;

use self::state::LiquidityRfqState;

pub struct LiquidityRfqContract {
    state: LiquidityRfqState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(LiquidityRfqContract);

impl WithContractAbi for LiquidityRfqContract {
    type Abi = LiquidityRfqAbi;
}

impl Contract for LiquidityRfqContract {
    type Message = ();
    type InstantiationArgument = ();
    type Parameters = LiquidityRfqParameters;

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = LiquidityRfqState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        LiquidityRfqContract { state, runtime }
    }

    async fn instantiate(&mut self, _argument: ()) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.initialized.set(true);

        // 1: If we're here and token pair has native token, native token amount should already
        //    been funded to router
        // 2: Authenticate token allowance
        self.approve_token_0_liquidity_funds();
    }

    // It must be run on creation chain
    // It means, if another application on another chain need to call back it, it should send a
    // message to its own application on this creation chain, then call it
    async fn execute_operation(
        &mut self,
        operation: LiquidityRfqOperation,
    ) -> LiquidityRfqResponse {
        if self.runtime.chain_id() != self.runtime.application_id().creation.chain_id {
            panic!("Operations must only be run on creation chain");
        }
        match operation {
            LiquidityRfqOperation::Approved { token } => {
                self.on_op_approved(token).expect("Failed OP: approved")
            }
            LiquidityRfqOperation::Rejected { token } => {
                self.on_op_rejected(token).expect("Failed OP: rejected")
            }
        }
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("LiquidityRfq application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl LiquidityRfqContract {
    fn token_0(&mut self) -> ApplicationId {
        self.runtime.application_parameters().token_0
    }

    fn amount_0(&mut self) -> Amount {
        self.runtime.application_parameters().amount_0
    }

    fn token_1(&mut self) -> Option<ApplicationId> {
        self.runtime.application_parameters().token_1
    }

    fn router_application_id(&mut self) -> ApplicationId {
        self.runtime.application_parameters().router_application_id
    }

    fn approve_token_liquidity_funds(&mut self, token: ApplicationId) {
        let chain_id = self.runtime.chain_id();
        let application_id = self.runtime.application_id().forget_abi();

        let call = MemeOperation::Approve {
            spender: AccountOwner::Application(self.router_application_id()),
            amount: self.amount_0(),
            rfq_application: Some(Account {
                chain_id,
                owner: Some(AccountOwner::Application(application_id)),
            }),
        };

        let _ = self
            .runtime
            .call_application(true, token.with_abi::<MemeAbi>(), &call);
    }

    fn approve_token_0_liquidity_funds(&mut self) {
        let token_0 = self.token_0();
        self.approve_token_liquidity_funds(token_0);
    }

    fn tokens_funded(&mut self) {
        // TODO: Notify router
    }

    fn tokens_rejected(&mut self) {
        // TODO: Notify router
    }

    fn validate_token(&mut self, token: ApplicationId) {
        if let Some(token_1) = self.token_1() {
            assert!(token == self.token_0() || token == token_1, "Invalid token");
        } else {
            assert!(token == self.token_0(), "Invalid token");
        }
    }

    fn return_token_0_funds(&mut self) {
        // TODO: return token_0 funds to caller
    }

    fn on_op_approved(
        &mut self,
        token: ApplicationId,
    ) -> Result<LiquidityRfqResponse, LiquidityRfqError> {
        self.validate_token(token);

        if let Some(token_1) = self.token_1() {
            if token == token_1 {
                self.tokens_funded();
                return Ok(LiquidityRfqResponse::Ok);
            }
            self.approve_token_liquidity_funds(token_1);
        } else {
            self.tokens_funded();
        }
        Ok(LiquidityRfqResponse::Ok)
    }

    fn on_op_rejected(
        &mut self,
        token: ApplicationId,
    ) -> Result<LiquidityRfqResponse, LiquidityRfqError> {
        self.validate_token(token);
        if let Some(token_1) = self.token_1() {
            if token == token_1 {
                self.return_token_0_funds();
            }
        }
        self.tokens_rejected();
        Ok(LiquidityRfqResponse::Ok)
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::liquidity_rfq::{
        LiquidityRfqAbi, LiquidityRfqOperation, LiquidityRfqParameters, LiquidityRfqResponse,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{Amount, ApplicationId, ChainId},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{LiquidityRfqContract, LiquidityRfqState};

    #[test]
    fn operation_approved() {
        let mut rfq = create_and_instantiate_liquidity_rfq();
        let token_0 = rfq.runtime.application_parameters().token_0;

        let response = rfq
            .execute_operation(LiquidityRfqOperation::Approved { token: token_0 })
            .now_or_never()
            .expect("Execution of liquidity rfq operation should not await anything");

        assert!(matches!(response, LiquidityRfqResponse::Ok));
    }

    #[test]
    fn operation_rejected() {
        let mut rfq = create_and_instantiate_liquidity_rfq();
        let token_0 = rfq.runtime.application_parameters().token_0;

        let response = rfq
            .execute_operation(LiquidityRfqOperation::Rejected { token: token_0 })
            .now_or_never()
            .expect("Execution of liquidity rfq operation should not await anything");

        assert!(matches!(response, LiquidityRfqResponse::Ok));
    }

    #[test]
    #[should_panic(expected = "Invalid token")]
    fn operation_approved_invalid_token() {
        let mut rfq = create_and_instantiate_liquidity_rfq();
        let token_id = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000003";
        let token_0 = ApplicationId::from_str(token_id).unwrap();

        let response = rfq
            .execute_operation(LiquidityRfqOperation::Approved { token: token_0 })
            .now_or_never()
            .expect("Execution of liquidity rfq operation should not await anything");

        assert!(matches!(response, LiquidityRfqResponse::Ok));
    }

    #[test]
    #[should_panic(expected = "Invalid token")]
    fn operation_reject_invalid_token() {
        let mut rfq = create_and_instantiate_liquidity_rfq();
        let token_id = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000003";
        let token_0 = ApplicationId::from_str(token_id).unwrap();

        let response = rfq
            .execute_operation(LiquidityRfqOperation::Rejected { token: token_0 })
            .now_or_never()
            .expect("Execution of liquidity rfq operation should not await anything");

        assert!(matches!(response, LiquidityRfqResponse::Ok));
    }

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn mock_application_call(
        _authenticated: bool,
        _application_id: ApplicationId,
        _operation: Vec<u8>,
    ) -> Vec<u8> {
        vec![0]
    }

    fn create_and_instantiate_liquidity_rfq() -> LiquidityRfqContract {
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str).unwrap();
        let router_application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000001";
        let router_application_id = ApplicationId::from_str(router_application_id_str).unwrap();
        let chain_id =
            ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46")
                .unwrap();
        let my_application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000008";
        let my_application_id = ApplicationId::from_str(my_application_id_str)
            .unwrap()
            .with_abi::<LiquidityRfqAbi>();
        let runtime = ContractRuntime::new()
            .with_application_parameters(LiquidityRfqParameters {
                token_0: application_id,
                token_1: None,
                amount_0: Amount::from_tokens(1),
                amount_1: None,
                router_application_id,
            })
            .with_chain_id(chain_id)
            .with_call_application_handler(mock_application_call)
            .with_application_id(my_application_id);
        let mut contract = LiquidityRfqContract {
            state: LiquidityRfqState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(())
            .now_or_never()
            .expect("Initialization of liquidity rfq state should not await anything");

        assert_eq!(*contract.state.initialized.get(), true);

        contract
    }
}
