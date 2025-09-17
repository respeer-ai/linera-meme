// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    policy::open_chain_fee_budget,
    proxy::{InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation, ProxyResponse},
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainId,
        ChainOwnership, ModuleId, TimeoutConfig, WithContractAbi,
    },
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy::ProxyError;

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
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        let owners = self.owner_accounts();
        self.state
            .instantiate(argument, owners)
            .await
            .expect("Failed instantiate");
    }

    async fn execute_operation(&mut self, operation: ProxyOperation) -> ProxyResponse {
        // All operations must be run on user chain side
        if self.runtime.chain_id() == self.runtime.application_creator_chain_id() {
            panic!("Operations must not be run on creation chain");
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

            ProxyOperation::RegisterMiner => self
                .on_op_register_miner()
                .expect("Failed OP: register miner"),
            ProxyOperation::DeregisterMiner => self
                .on_op_deregister_miner()
                .expect("Failed OP: deregister miner"),

            ProxyOperation::CreateMeme {
                meme_instantiation_argument,
                meme_parameters,
            } => self
                .on_op_create_meme(meme_instantiation_argument, meme_parameters)
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
        // All messages must be run on right chain
        if !self.message_executable(&message) {
            panic!("Messages must only be run on right chain: {:?}", message);
        }

        match message {
            ProxyMessage::ProposeAddGenesisMiner { operator, owner } => self
                .on_msg_propose_add_genesis_miner(operator, owner)
                .await
                .expect("Failed MSG: propose add genesis miner"),
            ProxyMessage::ApproveAddGenesisMiner { operator, owner } => self
                .on_msg_approve_add_genesis_miner(operator, owner)
                .await
                .expect("Failed MSG: approve add genesis miner"),

            ProxyMessage::ProposeRemoveGenesisMiner { operator, owner } => self
                .on_msg_propose_remove_genesis_miner(operator, owner)
                .await
                .expect("Failed MSG: propose remove genesis miner"),
            ProxyMessage::ApproveRemoveGenesisMiner { operator, owner } => self
                .on_msg_approve_remove_genesis_miner(operator, owner)
                .await
                .expect("Failed MSG: approve remove genesis miner"),

            ProxyMessage::RegisterMiner { owner } => self
                .on_msg_register_miner(owner)
                .await
                .expect("Failed MSG: register miner"),
            ProxyMessage::DeregisterMiner { owner } => self
                .on_msg_deregister_miner(owner)
                .expect("Failed MSG: deregister miner"),

            ProxyMessage::CreateMeme {
                instantiation_argument,
                parameters,
            } => self
                .on_msg_create_meme(instantiation_argument, parameters)
                .await
                .expect("Failed MSG: create meme"),
            ProxyMessage::CreateMemeExt {
                bytecode_id,
                instantiation_argument,
                parameters,
            } => self
                .on_msg_create_meme_ext(bytecode_id, instantiation_argument, parameters)
                .await
                .expect("Failed MSG: create meme ext"),
            ProxyMessage::MemeCreated { chain_id, token } => self
                .on_msg_meme_created(chain_id, token)
                .await
                .expect("Failed MSG: meme created"),

            ProxyMessage::ProposeAddOperator { operator, owner } => self
                .on_msg_propose_add_operator(operator, owner)
                .await
                .expect("Failed MSG: propose add operator"),
            ProxyMessage::ApproveAddOperator { operator, owner } => self
                .on_msg_approve_add_operator(operator, owner)
                .await
                .expect("Failed MSG: approve add operator"),

            ProxyMessage::ProposeBanOperator { operator, owner } => self
                .on_msg_propose_ban_operator(operator, owner)
                .await
                .expect("Failed MSG: propose ban operator"),
            ProxyMessage::ApproveBanOperator { operator, owner } => self
                .on_msg_approve_ban_operator(operator, owner)
                .await
                .expect("Failed MSG: approve ban operator"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl ProxyContract {
    fn message_executable(&mut self, message: &ProxyMessage) -> bool {
        match message {
            ProxyMessage::CreateMemeExt { .. } => {
                self.runtime.chain_id() != self.runtime.application_creator_chain_id()
            }
            _ => self.runtime.chain_id() == self.runtime.application_creator_chain_id(),
        }
    }

    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: self.runtime.authenticated_signer().unwrap(),
        }
    }

    fn owner_accounts(&mut self) -> Vec<Account> {
        let chain_id = self.runtime.chain_id();
        self.runtime
            .chain_ownership()
            .all_owners()
            .map(|&owner| Account { chain_id, owner })
            .collect()
    }

    fn on_op_propose_add_genesis_miner(
        &mut self,
        owner: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ProposeAddGenesisMiner { operator, owner })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_add_genesis_miner(
        &mut self,
        owner: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ApproveAddGenesisMiner { operator, owner })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_remove_genesis_miner(
        &mut self,
        owner: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ProposeRemoveGenesisMiner { operator, owner })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_remove_genesis_miner(
        &mut self,
        owner: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ApproveRemoveGenesisMiner { operator, owner })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_register_miner(&mut self) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::RegisterMiner { owner })
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_deregister_miner(&mut self) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::DeregisterMiner { owner })
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn fund_proxy_chain(&mut self, to: AccountOwner, amount: Amount) {
        assert!(amount > Amount::ZERO, "Invalid fund amount");

        let creator = self.runtime.authenticated_signer().unwrap();
        let chain_id = self.runtime.application_creator_chain_id();

        let owner_balance = self.runtime.owner_balance(creator);
        let chain_balance = self.runtime.chain_balance();

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount <= owner_balance {
            Amount::ZERO
        } else {
            amount.try_sub(owner_balance).expect("Invalid amount")
        };

        assert!(from_owner_balance <= owner_balance, "Insufficient balance");
        assert!(from_chain_balance <= chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime.transfer(
                creator,
                Account {
                    chain_id,
                    owner: to,
                },
                from_owner_balance,
            );
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.transfer(
                AccountOwner::CHAIN,
                Account {
                    chain_id,
                    owner: to,
                },
                from_chain_balance,
            );
        }
    }

    fn fund_proxy_chain_fee_budget(&mut self, fund_pool_fee: bool) {
        // Open chain budget fee for meme chain
        self.fund_proxy_chain(AccountOwner::CHAIN, open_chain_fee_budget());
        if !fund_pool_fee {
            return;
        }
        // Open chain budget fee for pool chain
        let signer = self.runtime.authenticated_signer().unwrap();
        self.fund_proxy_chain(signer, open_chain_fee_budget());
    }

    fn fund_proxy_chain_initial_liquidity(&mut self, meme_parameters: MemeParameters) {
        if meme_parameters.virtual_initial_liquidity {
            return;
        }
        let Some(liquidity) = meme_parameters.initial_liquidity else {
            return;
        };
        // We cannot fund to application directly. Due to we're not owner of the chain then we
        // cannot transfer the fund to swap. We should fund ourself on the target chain
        // let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
        let signer = self.runtime.authenticated_signer().unwrap();
        self.fund_proxy_chain(signer, liquidity.native_amount);
    }

    fn on_op_create_meme(
        &mut self,
        mut meme_instantiation_argument: MemeInstantiationArgument,
        mut meme_parameters: MemeParameters,
    ) -> Result<ProxyResponse, ProxyError> {
        meme_instantiation_argument.proxy_application_id =
            Some(self.runtime.application_id().forget_abi());
        meme_instantiation_argument.meme.virtual_initial_liquidity =
            meme_parameters.virtual_initial_liquidity;
        meme_instantiation_argument.meme.initial_liquidity =
            meme_parameters.initial_liquidity.clone();

        // Fund proxy application on the creation chain, it'll fund meme chain for fee and
        // initial liquidity
        self.fund_proxy_chain_fee_budget(meme_parameters.initial_liquidity.is_some());
        self.fund_proxy_chain_initial_liquidity(meme_parameters.clone());

        meme_parameters.creator = self.owner_account();

        self.runtime
            .prepare_message(ProxyMessage::CreateMeme {
                instantiation_argument: meme_instantiation_argument,
                parameters: meme_parameters,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_add_operator(
        &mut self,
        operator: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ProposeAddOperator {
                operator: owner,
                owner: operator,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_add_operator(
        &mut self,
        operator: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ApproveAddOperator {
                operator: owner,
                owner: operator,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_propose_ban_operator(
        &mut self,
        operator: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ProposeBanOperator {
                operator: owner,
                owner: operator,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    fn on_op_approve_ban_operator(
        &mut self,
        operator: Account,
    ) -> Result<ProxyResponse, ProxyError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(ProxyMessage::ApproveBanOperator {
                operator: owner,
                owner: operator,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(ProxyResponse::Ok)
    }

    async fn on_msg_propose_add_genesis_miner(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.add_genesis_miner(owner).await?;
        // Everybody can propose add genesis miner. If it's proposed by operator, approve it
        self.state.validate_operator(operator).await?;
        self.state.approve_add_genesis_miner(owner, operator).await
    }

    async fn on_msg_approve_add_genesis_miner(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.validate_operator(operator).await?;
        self.state.approve_add_genesis_miner(owner, operator).await
    }

    async fn on_msg_propose_remove_genesis_miner(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.remove_genesis_miner(owner).await?;
        self.state.validate_operator(operator).await?;
        self.state
            .approve_remove_genesis_miner(owner, operator)
            .await
    }

    async fn on_msg_approve_remove_genesis_miner(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.validate_operator(operator).await?;
        self.state
            .approve_remove_genesis_miner(owner, operator)
            .await
    }

    async fn on_msg_register_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
        self.state.register_miner(owner).await
    }

    fn on_msg_deregister_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
        self.state.deregister_miner(owner)
    }

    async fn meme_chain_owner_weights(&self) -> Result<Vec<(AccountOwner, u64)>, ProxyError> {
        let mut owner_weights = Vec::new();

        for owner in self.state.genesis_miner_owners().await? {
            owner_weights.push((owner, 200 as u64))
        }
        for owner in self.state.miner_owners().await? {
            owner_weights.push((owner, 100 as u64))
        }

        Ok(owner_weights)
    }

    async fn create_meme_chain(&mut self) -> Result<ChainId, ProxyError> {
        let ownership = ChainOwnership::multiple(
            self.meme_chain_owner_weights().await?,
            0, // TODO: run in single leader mode firstly, will be updated when multi leader mode done
            TimeoutConfig::default(),
        );
        let application_id = self.runtime.application_id().forget_abi();
        // We have to let meme application change permissions
        let permissions = ApplicationPermissions {
            execute_operations: Some(vec![application_id]),
            // Don't mandatory any application
            mandatory_applications: vec![],
            close_chain: vec![application_id],
            change_application_permissions: vec![application_id],
            call_service_as_oracle: Some(vec![application_id]),
            make_http_requests: Some(vec![application_id]),
        };
        Ok(self
            .runtime
            .open_chain(ownership, permissions, open_chain_fee_budget()))
    }

    fn fund_meme_chain_initial_liquidity(
        &mut self,
        meme_chain_id: ChainId,
        parameters: MemeParameters,
    ) {
        // We always deduct one for pool chain
        let mut amount = match parameters.initial_liquidity {
            Some(_) => open_chain_fee_budget(),
            None => Amount::ZERO,
        };

        // Balance is already fund to signer on proxy chain, so we transfer to meme chain
        let signer = self.runtime.authenticated_signer().unwrap();
        let balance = self.runtime.owner_balance(signer);

        if let Some(liquidity) = parameters.initial_liquidity {
            if !parameters.virtual_initial_liquidity {
                amount = amount.try_add(liquidity.native_amount).unwrap();
            }
        };

        if amount <= Amount::ZERO {
            return;
        }

        assert!(
            balance >= amount,
            "User on proxy chain should already funded ({} < {})",
            balance,
            amount
        );

        self.runtime.transfer(
            signer,
            Account {
                chain_id: meme_chain_id,
                owner: signer,
            },
            amount,
        );
    }

    async fn on_creation_chain_msg_create_meme(
        &mut self,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> Result<(), ProxyError> {
        // 1: create a new chain which allow and mandary proxy
        let chain_id = self.create_meme_chain().await?;

        // Fund created meme chain with initial liquidity
        self.fund_meme_chain_initial_liquidity(chain_id, parameters.clone());

        let bytecode_id = self.state.meme_bytecode_id().await;

        // 2: Send create meme message to target chain
        self.runtime
            .prepare_message(ProxyMessage::CreateMemeExt {
                bytecode_id,
                instantiation_argument,
                parameters,
            })
            .with_authentication()
            .send_to(chain_id);

        self.state
            .create_chain(chain_id, self.runtime.system_time())
            .await
    }

    fn create_meme_application(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> ApplicationId {
        // It should be always run on target chain
        self.runtime
            .create_application::<ProxyAbi, MemeParameters, MemeInstantiationArgument>(
                bytecode_id,
                &parameters,
                &instantiation_argument,
                vec![],
            )
            .forget_abi()
    }

    async fn on_meme_chain_msg_create_meme(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> Result<(), ProxyError> {
        // 1: Create meme application
        let application_id =
            self.create_meme_application(bytecode_id, instantiation_argument, parameters);

        let permissions = ApplicationPermissions {
            execute_operations: Some(vec![application_id]),
            // Don't mandatory any application
            mandatory_applications: vec![],
            close_chain: vec![application_id],
            change_application_permissions: vec![application_id],
            call_service_as_oracle: Some(vec![application_id]),
            make_http_requests: Some(vec![application_id]),
        };
        self.runtime
            .change_application_permissions(permissions)
            .expect("Failed change application permissions");

        // We're now on meme chain, notify proxy creation chain to store token info
        let meme_chain_id = self.runtime.chain_id();
        let proxy_chain_id = self.runtime.application_creator_chain_id();
        self.runtime
            .prepare_message(ProxyMessage::MemeCreated {
                chain_id: meme_chain_id,
                token: application_id,
            })
            .with_authentication()
            .send_to(proxy_chain_id);

        Ok(())
    }

    async fn on_msg_create_meme(
        &mut self,
        mut meme: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> Result<(), ProxyError> {
        meme.swap_application_id = Some(self.state.swap_application_id().await);
        self.on_creation_chain_msg_create_meme(meme, parameters)
            .await
    }

    async fn on_msg_create_meme_ext(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> Result<(), ProxyError> {
        self.on_meme_chain_msg_create_meme(bytecode_id, instantiation_argument, parameters)
            .await
    }

    async fn on_msg_meme_created(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), ProxyError> {
        self.state.create_chain_token(chain_id, token).await
    }

    async fn on_msg_propose_add_operator(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.add_operator(owner).await?;
        // Everybody can propose add genesis miner. If it's proposed by operator, approve it
        self.state.validate_operator(operator).await?;
        self.state.approve_add_operator(owner, operator).await
    }

    async fn on_msg_approve_add_operator(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.validate_operator(operator).await?;
        self.state.approve_add_operator(owner, operator).await
    }

    async fn on_msg_propose_ban_operator(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.ban_operator(owner).await?;
        // Everybody can propose add genesis miner. If it's proposed by operator, approve it
        self.state.validate_operator(operator).await?;
        self.state.approve_ban_operator(owner, operator).await
    }

    async fn on_msg_approve_ban_operator(
        &mut self,
        operator: Account,
        owner: Account,
    ) -> Result<(), ProxyError> {
        self.state.validate_operator(operator).await?;
        self.state.approve_ban_operator(owner, operator).await
    }
}

#[cfg(test)]
mod tests {
    use abi::proxy::{
        InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation, ProxyResponse,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        linera_base_types::{
            Account, AccountOwner, ApplicationId, ChainId, ChainOwnership, ModuleId,
        },
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{ProxyContract, ProxyState};

    #[test]
    #[should_panic(expected = "Operations must not be run on creation chain")]
    fn op_propose_add_genesis_miner() {
        let _ = env_logger::builder().is_test(true).try_init();
        let mut proxy = create_and_instantiate_proxy();

        let owner = AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
        )
        .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let owner = Account { chain_id, owner };

        let response = proxy
            .execute_operation(ProxyOperation::ProposeAddGenesisMiner { owner })
            .now_or_never()
            .expect("Execution of proxy operation should not await anything");

        assert!(matches!(response, ProxyResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn msg_propose_add_genesis_miner() {
        let _ = env_logger::builder().is_test(true).try_init();
        let mut proxy = create_and_instantiate_proxy();

        let owner = AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let operator = Account { chain_id, owner };
        let owner = AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
        )
        .unwrap();
        let owner = Account { chain_id, owner };

        proxy
            .execute_message(ProxyMessage::ProposeAddGenesisMiner { operator, owner })
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
    }

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_proxy() -> ProxyContract {
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let owner = AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap();
        let operator = Account { chain_id, owner };
        let application_id = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap()
        .with_abi::<ProxyAbi>();
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_signer(owner)
            .with_chain_id(chain_id)
            .with_application_creator_chain_id(chain_id)
            .with_chain_ownership(ChainOwnership::single(owner))
            .with_application_id(application_id);
        let mut contract = ProxyContract {
            state: ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let meme_bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();

        contract
            .instantiate(InstantiationArgument {
                meme_bytecode_id,
                operators: vec![operator],
                swap_application_id: application_id.forget_abi(),
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
