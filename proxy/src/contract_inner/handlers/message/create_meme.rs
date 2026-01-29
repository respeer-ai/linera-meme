use crate::interfaces::state::StateInterface;
use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    policy::open_chain_fee_budget,
    proxy::{ProxyMessage, ProxyResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationPermissions, ChainId, ChainOwnership, TimeoutConfig,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreateMemeHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateMemeHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::CreateMeme {
            instantiation_argument,
            parameters,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            instantiation_argument: instantiation_argument.clone(),
            parameters: parameters.clone(),
        }
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
        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        let balance = self.runtime.borrow_mut().owner_balance(signer);

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

        self.runtime.borrow_mut().transfer(
            signer,
            Account {
                chain_id: meme_chain_id,
                owner: signer,
            },
            amount,
        );
    }

    async fn meme_chain_owner_weights(&self) -> Result<Vec<(AccountOwner, u64)>, HandlerError> {
        let mut owner_weights = Vec::new();

        for miner in self.state.miners().await.map_err(Into::into)? {
            if self
                .state
                .is_genesis_miner(miner.owner)
                .await
                .map_err(Into::into)?
            {
                owner_weights.push((miner.owner.owner, 200 as u64))
            } else {
                owner_weights.push((miner.owner.owner, 100 as u64))
            }
        }

        Ok(owner_weights)
    }

    async fn create_meme_chain(&mut self) -> Result<ChainId, HandlerError> {
        // We must let current owners to produce block for meme chain at the beginning
        // It'll be changed to open_multi_leader_rounds in meme application on meme chain
        let ownership = ChainOwnership::multiple(
            self.meme_chain_owner_weights().await?,
            0,
            TimeoutConfig::default(),
        );

        let application_id = self.runtime.borrow_mut().application_id().forget_abi();
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
            .borrow_mut()
            .open_chain(ownership, permissions, open_chain_fee_budget()))
    }

    async fn on_creation_chain_msg_create_meme(
        &mut self,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> Result<HandlerOutcome<ProxyMessage, ProxyResponse>, HandlerError> {
        // 1: create a new chain which allow and mandary proxy
        let chain_id = self.create_meme_chain().await?;

        // Fund created meme chain with initial liquidity
        self.fund_meme_chain_initial_liquidity(chain_id, parameters.clone());

        let bytecode_id = self.state.meme_bytecode_id();

        let destination = chain_id;
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            ProxyMessage::CreateMemeExt {
                bytecode_id,
                instantiation_argument,
                parameters,
            },
        );

        self.state
            .create_chain(chain_id, self.runtime.borrow_mut().system_time())
            .map_err(Into::into)?;

        Ok(outcome)
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for CreateMemeHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        self.instantiation_argument.swap_application_id = Some(self.state.swap_application_id());

        Ok(Some(
            self.on_creation_chain_msg_create_meme(
                self.instantiation_argument.clone(),
                self.parameters.clone(),
            )
            .await?,
        ))
    }
}
