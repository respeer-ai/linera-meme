// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::meme::InstantiationArgument as MemeInstantiationArgument;
use abi::meme::Parameters as MemeParameters;
use linera_sdk::{
    base::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, BytecodeId, ChainId,
        ChainOwnership, MessageId, Owner, TimeoutConfig, WithContractAbi,
    },
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
        self.state
            .initantiate(argument, owner)
            .await
            .expect("Failed instantiate");
    }

    async fn execute_operation(&mut self, operation: ProxyOperation) -> ProxyResponse {
        // All operations must be run on user chain side
        if self.runtime.chain_id() == self.runtime.application_id().creation.chain_id {
            panic!("Operations must not be run on creation chain");
        }

        match operation {
            ProxyOperation::ProposeAddGenesisMiner { owner, endpoint } => self
                .on_op_propose_add_genesis_miner(owner, endpoint)
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

            ProxyOperation::RegisterMiner { endpoint } => self
                .on_op_register_miner(endpoint)
                .expect("Failed OP: register miner"),
            ProxyOperation::DeregisterMiner => self
                .on_op_deregister_miner()
                .expect("Failed OP: deregister miner"),

            ProxyOperation::CreateMeme {
                fee_budget,
                meme_instantiation_argument,
            } => self
                .on_op_create_meme(fee_budget, meme_instantiation_argument)
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
        }
    }

    async fn execute_message(&mut self, message: ProxyMessage) {
        // All messages must be run on creation chain side
        if self.runtime.chain_id() != self.runtime.application_id().creation.chain_id {
            panic!("Messages must only be run on creation chain");
        }

        match message {
            ProxyMessage::ProposeAddGenesisMiner { owner, endpoint } => self
                .on_msg_propose_add_genesis_miner(owner, endpoint)
                .await
                .expect("Failed MSG: propose add genesis miner"),
            ProxyMessage::ApproveAddGenesisMiner { owner } => self
                .on_msg_approve_add_genesis_miner(owner)
                .await
                .expect("Failed MSG: approve add genesis miner"),

            ProxyMessage::ProposeRemoveGenesisMiner { owner } => self
                .on_msg_propose_remove_genesis_miner(owner)
                .await
                .expect("Failed MSG: propose remove genesis miner"),
            ProxyMessage::ApproveRemoveGenesisMiner { owner } => self
                .on_msg_approve_remove_genesis_miner(owner)
                .await
                .expect("Failed MSG: approve remove genesis miner"),

            ProxyMessage::RegisterMiner { endpoint } => self
                .on_msg_register_miner(endpoint)
                .expect("Failed MSG: register miner"),
            ProxyMessage::DeregisterMiner => self
                .on_msg_deregister_miner()
                .expect("Failed MSG: deregister miner"),

            ProxyMessage::CreateMeme {
                fee_budget,
                instantiation_argument,
            } => self
                .on_msg_create_meme(fee_budget, instantiation_argument)
                .await
                .expect("Failed MSG: create meme"),
            ProxyMessage::CreateMemeExt {
                creator,
                bytecode_id,
                instantiation_argument,
            } => self
                .on_msg_create_meme_ext(creator, bytecode_id, instantiation_argument)
                .expect("Failed MSG: create meme ext"),

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
        endpoint: Option<String>,
    ) -> Result<ProxyResponse, ProxyError> {
        self.runtime
            .prepare_message(ProxyMessage::ProposeAddGenesisMiner { owner, endpoint })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_add_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        self.runtime
            .prepare_message(ProxyMessage::ApproveAddGenesisMiner { owner })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        self.runtime
            .prepare_message(ProxyMessage::ProposeRemoveGenesisMiner { owner })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<ProxyResponse, ProxyError> {
        self.runtime
            .prepare_message(ProxyMessage::ApproveRemoveGenesisMiner { owner })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
        Ok(ProxyResponse::Ok)
    }

    fn on_op_register_miner(
        &mut self,
        endpoint: Option<String>,
    ) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_deregister_miner(&mut self) -> Result<ProxyResponse, ProxyError> {
        Ok(ProxyResponse::Ok)
    }

    fn on_op_create_meme(
        &mut self,
        fee_budget: Option<Amount>,
        meme_instantiation_argument: MemeInstantiationArgument,
    ) -> Result<ProxyResponse, ProxyError> {
        // Fix amount token will be transferred to meme chain as fee
        let creator = self.runtime.authenticated_signer().unwrap();
        let chain_id = self.runtime.application_id().creation.chain_id;
        let application_id = self.runtime.application_id().forget_abi();
        let fee_budget = fee_budget.unwrap_or(Amount::ONE);

        if fee_budget > Amount::ZERO {
            self.runtime.transfer(
                Some(AccountOwner::User(creator)),
                Account {
                    chain_id,
                    owner: Some(AccountOwner::Application(application_id)),
                },
                fee_budget,
            );
        }

        self.runtime
            .prepare_message(ProxyMessage::CreateMeme {
                fee_budget,
                instantiation_argument: meme_instantiation_argument,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
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

    async fn on_msg_propose_add_genesis_miner(
        &mut self,
        owner: Owner,
        endpoint: Option<String>,
    ) -> Result<(), ProxyError> {
        self.state.add_genesis_miner(owner, endpoint).await?;
        let signer = self.runtime.authenticated_signer().unwrap();
        if self.state.validate_operator(signer).await? {
            return self.state.approve_add_genesis_miner(owner, signer).await;
        }
        Ok(())
    }

    async fn on_msg_approve_add_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        self.state
            .approve_add_genesis_miner(owner, self.runtime.authenticated_signer().unwrap())
            .await
    }

    async fn on_msg_propose_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<(), ProxyError> {
        self.state.remove_genesis_miner(owner).await?;
        let signer = self.runtime.authenticated_signer().unwrap();
        if self.state.validate_operator(signer).await? {
            return self.state.approve_remove_genesis_miner(owner, signer).await;
        }
        Ok(())
    }

    async fn on_msg_approve_remove_genesis_miner(
        &mut self,
        owner: Owner,
    ) -> Result<(), ProxyError> {
        self.state
            .approve_remove_genesis_miner(owner, self.runtime.authenticated_signer().unwrap())
            .await
    }

    fn on_msg_register_miner(&mut self, endpoint: Option<String>) -> Result<(), ProxyError> {
        Ok(())
    }

    fn on_msg_deregister_miner(&mut self) -> Result<(), ProxyError> {
        Ok(())
    }

    async fn meme_chain_owner_weights(&self) -> Result<Vec<(Owner, u64)>, ProxyError> {
        let mut owner_weights = Vec::new();

        for owner in self.state.genesis_miners().await? {
            owner_weights.push((owner, 200 as u64))
        }
        for owner in self.state.miners().await? {
            owner_weights.push((owner, 100 as u64))
        }

        Ok(owner_weights)
    }

    async fn create_meme_chain(
        &mut self,
        fee_budget: Amount,
    ) -> Result<(MessageId, ChainId), ProxyError> {
        let ownership = ChainOwnership::multiple(
            self.meme_chain_owner_weights().await?,
            0, // TODO: run in single leader mode firstly, will be updated when multi leader mode done
            TimeoutConfig::default(),
        );
        let application_id = self.runtime.application_id();
        let permissions = ApplicationPermissions::new_single(application_id.forget_abi());
        Ok(self.runtime.open_chain(ownership, permissions, fee_budget))
    }

    async fn on_creation_chain_msg_create_meme(
        &mut self,
        fee_budget: Amount,
        instantiation_argument: MemeInstantiationArgument,
    ) -> Result<(), ProxyError> {
        // 1: create a new chain which allow and mandary proxy
        let (message_id, chain_id) = self.create_meme_chain(fee_budget).await?;

        let bytecode_id = self.state.meme_bytecode_id().await;
        let creator = self.runtime.authenticated_signer().unwrap();

        // 2: Send create meme message to target chain
        self.runtime
            .prepare_message(ProxyMessage::CreateMemeExt {
                creator,
                bytecode_id,
                instantiation_argument,
            })
            .with_authentication()
            .send_to(chain_id);

        self.state
            .create_chain(chain_id, message_id, self.runtime.system_time())
            .await
    }

    fn create_meme_application(
        &mut self,
        bytecode_id: BytecodeId,
        instantiation_argument: MemeInstantiationArgument,
    ) -> ApplicationId {
        // It should be always run on target chain
        self.runtime
            .create_application::<ProxyAbi, MemeParameters, MemeInstantiationArgument>(
                bytecode_id,
                &MemeParameters {},
                &instantiation_argument,
                vec![],
            )
            .forget_abi()
    }

    fn on_meme_chain_msg_create_meme(
        &mut self,
        creator: Owner,
        bytecode_id: BytecodeId,
        instantiation_argument: MemeInstantiationArgument,
    ) -> Result<(), ProxyError> {
        // 1: Create meme application
        let _ = self.create_meme_application(bytecode_id, instantiation_argument);
        Ok(())
    }

    async fn on_msg_create_meme(
        &mut self,
        fee_budget: Amount,
        meme: MemeInstantiationArgument,
    ) -> Result<(), ProxyError> {
        self.on_creation_chain_msg_create_meme(fee_budget, meme)
            .await
    }

    fn on_msg_create_meme_ext(
        &mut self,
        creator: Owner,
        bytecode_id: BytecodeId,
        instantiation_argument: MemeInstantiationArgument,
    ) -> Result<(), ProxyError> {
        self.on_meme_chain_msg_create_meme(creator, bytecode_id, instantiation_argument)
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
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{
        base::{ApplicationId, BytecodeId, ChainId, Owner},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use proxy::{InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation, ProxyResponse};
    use std::str::FromStr;

    use super::{ProxyContract, ProxyState};

    #[test]
    #[should_panic(expected = "Operations must not be run on creation chain")]
    fn op_propose_add_genesis_miner() {
        let mut proxy = create_and_instantiate_proxy();

        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();

        let response = proxy
            .execute_operation(ProxyOperation::ProposeAddGenesisMiner {
                owner,
                endpoint: None,
            })
            .now_or_never()
            .expect("Execution of proxy operation should not await anything");

        assert!(matches!(response, ProxyResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn msg_propose_add_genesis_miner() {
        let mut proxy = create_and_instantiate_proxy();

        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();

        proxy
            .execute_message(ProxyMessage::ProposeAddGenesisMiner {
                owner,
                endpoint: None,
            })
            .await;

        assert_eq!(
            proxy
                .state
                .genesis_miners
                .contains_key(&owner)
                .await
                .unwrap(),
            true
        );

        let miner = proxy
            .state
            .genesis_miners
            .get(&owner)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(miner.endpoint, None);
    }

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_proxy() -> ProxyContract {
        let operator =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let chain_id =
            ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46")
                .unwrap();
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str)
            .unwrap()
            .with_abi::<ProxyAbi>();
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_signer(operator)
            .with_chain_id(chain_id)
            .with_application_id(application_id);
        let mut contract = ProxyContract {
            state: ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let meme_bytecode_id = BytecodeId::from_str("58cc6e264a19cddf027010db262ca56a18e7b63e2a7ad1561ea9841f9aef308fc5ae59261c0137891a342001d3d4446a26c3666ed81aadf7e5eec6a01c86db6d").unwrap();

        contract
            .instantiate(InstantiationArgument {
                meme_bytecode_id,
                operator,
            })
            .now_or_never()
            .expect("Initialization of proxy state should not await anything");

        assert_eq!(
            contract.state.meme_bytecode_id.get().unwrap(),
            meme_bytecode_id
        );

        contract
    }
}
