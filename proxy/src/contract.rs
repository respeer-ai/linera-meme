// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::meme::InstantiationArgument as MemeInstantiationArgument;
use linera_sdk::{
    base::{Owner, WithContractAbi},
    ensure,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy::{
    InstantiationArgument, ProxyAbi, ProxyError, ProxyMessage, ProxyOperation, ProxyResponse,
};

use self::state::ProxyState;

pub struct ProxyContract {
    state: ProxyState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(ProxyContract);

impl WithContractAbi for ProxyContract {
    type Abi = ProxyAbi;
}

impl Contract for ProxyContract {
    type Message = ProxyMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        let owner = self
            .runtime
            .authenticated_signer()
            .expect("Invalid creator");
        self.state.initantiate(argument, owner).await;
    }

    async fn execute_operation(&mut self, operation: ProxyOperation) -> ProxyResponse {
        // All operations must be run on user chain side
        if self.runtime.chain_id() == self.runtime.application_id().creation.chain_id {
            panic!("Operation must not be run on creation chain");
        }

        match operation {
            ProxyOperation::ProposeAddGenesisMiner { owner } => self
                .on_op_propose_add_genesis_miner(owner)
                .expect("Failed OP: propose add genesis miner"),
            ProxyOperation::ApproveAddGenesisMiner { owner } => self
                .on_op_approve_add_genesis_miner(owner)
                .expect("Failed OP: approve add genesis miner"),

            ProxyOperation::ProposeRemoveGenesisMiner { owner } => self
                .on_op_propose_remove_genesis_miner(owner)
                .expect("Failed OP: propose remove genesis miner"),
            ProxyOperation::ApproveRemoveGenesisMiner { owner } => self
                .on_op_approve_remove_genesis_miner(owner)
                .expect("Failed OP: approve remove genesis miner"),

            ProxyOperation::RegisterMiner { owner } => self
                .on_op_register_miner(owner)
                .expect("Failed OP: register miner"),
            ProxyOperation::DeregisterMiner { owner } => self
                .on_op_deregister_miner(owner)
                .expect("Failed OP: deregister miner"),

            ProxyOperation::CreateMeme {
                meme_instantiation_argument,
            } => self
                .on_op_create_meme(meme_instantiation_argument)
                .expect("Failed OP: create meme"),

            ProxyOperation::ProposeAddOperator { owner } => self
                .on_op_propose_add_operator(owner)
                .expect("Failed OP: propose add operator"),
            ProxyOperation::ApproveAddOperator { owner } => self
                .on_op_approve_add_operator(owner)
                .expect("Failed OP: approve add operator"),

            ProxyOperation::ProposeBanOperator { owner } => self
                .on_op_propose_ban_operator(owner)
                .expect("Failed OP: propose ban operator"),
            ProxyOperation::ApproveBanOperator { owner } => self
                .on_op_approve_ban_operator(owner)
                .expect("Failed OP: approve ban operator"),

            ProxyOperation::Subscribe => {
                self.on_op_subscribe().expect("Failed OP: subscribe event")
            }
        }
    }

    async fn execute_message(&mut self, message: ProxyMessage) {
        // All messages must be run on creation chain side
        if self.runtime.chain_id() != self.runtime.application_id().creation.chain_id {
            panic!("Operation must be run on creation chain");
        }

        match message {
            ProxyMessage::ProposeAddGenesisMiner { owner } => self
                .on_msg_propose_add_genesis_miner(owner)
                .expect("Failed MSG: propose add genesis miner"),
            ProxyMessage::ApproveAddGenesisMiner { owner } => self
                .on_msg_approve_add_genesis_miner(owner)
                .expect("Failed MSG: approve add genesis miner"),

            ProxyMessage::ProposeRemoveGenesisMiner { owner } => self
                .on_msg_propose_remove_genesis_miner(owner)
                .expect("Failed MSG: propose remove genesis miner"),
            ProxyMessage::ApproveRemoveGenesisMiner { owner } => self
                .on_msg_approve_remove_genesis_miner(owner)
                .expect("Failed MSG: approve remove genesis miner"),

            ProxyMessage::RegisterMiner { owner } => self
                .on_msg_register_miner(owner)
                .expect("Failed MSG: register miner"),
            ProxyMessage::DeregisterMiner { owner } => self
                .on_msg_deregister_miner(owner)
                .expect("Failed MSG: deregister miner"),

            ProxyMessage::CreateMeme {
                meme_instantiation_argument,
            } => self
                .on_msg_create_meme(meme_instantiation_argument)
                .expect("Failed MSG: create meme"),

            ProxyMessage::ProposeAddOperator { owner } => self
                .on_msg_propose_add_operator(owner)
                .expect("Failed MSG: propose add operator"),
            ProxyMessage::ApproveAddOperator { owner } => self
                .on_msg_approve_add_operator(owner)
                .expect("Failed MSG: approve add operator"),

            ProxyMessage::ProposeBanOperator { owner } => self
                .on_msg_propose_ban_operator(owner)
                .expect("Failed MSG: propose ban operator"),
            ProxyMessage::ApproveBanOperator { owner } => self
                .on_msg_approve_ban_operator(owner)
                .expect("Failed MSG: approve ban operator"),

            ProxyMessage::Subscribe => self
                .on_msg_subscribe()
                .expect("Failed MSG: subscribe event"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl ProxyContract {
    fn on_op_propose_add_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_add_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_register_miner(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_deregister_miner(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_create_meme(
        &mut self,
        meme: MemeInstantiationArgument,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_add_operator(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_add_operator(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_ban_operator(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_ban_operator(&mut self, owner: Owner) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_subscribe(&mut self) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_msg_propose_add_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_approve_add_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_propose_remove_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_approve_remove_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_register_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_deregister_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_create_meme(&mut self, meme: MemeInstantiationArgument) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_propose_add_operator(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_approve_add_operator(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_propose_ban_operator(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_approve_ban_operator(&mut self, owner: Owner) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_subscribe(&mut self) -> Result<(), ProxyError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{
        base::BytecodeId, util::BlockingWait, views::View, Contract, ContractRuntime,
    };
    use proxy::InstantiationArgument;
    use std::str::FromStr;

    use super::{ProxyContract, ProxyState};

    #[test]
    fn operation() {}

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_proxy() -> ProxyContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = ProxyContract {
            state: ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let meme_bytecode_id = BytecodeId::from_str("58cc6e264a19cddf027010db262ca56a18e7b63e2a7ad1561ea9841f9aef308fc5ae59261c0137891a342001d3d4446a26c3666ed81aadf7e5eec6a01c86db6d").unwrap();

        contract
            .instantiate(InstantiationArgument { meme_bytecode_id })
            .now_or_never()
            .expect("Initialization of proxy state should not await anything");

        assert_eq!(
            contract.state.meme_bytecode_id.get().unwrap(),
            meme_bytecode_id
        );

        contract
    }
}
