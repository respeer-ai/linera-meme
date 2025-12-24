use crate::interfaces::state::StateInterface;
use abi::swap::{
    pool::{InstantiationArgument as PoolInstantiationArgument, PoolAbi, PoolParameters},
    router::SwapMessage,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, ChainId, ModuleId,
};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct CreatePoolHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    creator: Account,
    pool_bytecode_id: ModuleId,
    token_0_creator_chain_id: ChainId,
    token_0: ApplicationId,
    token_1_creator_chain_id: Option<ChainId>,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    virtual_initial_liquidity: bool,
    to: Option<Account>,
    user_pool: bool,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    CreatePoolHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::CreatePool {
            creator,
            pool_bytecode_id,
            token_0,
            token_1,
            amount_0,
            amount_1,
            virtual_initial_liquidity,
            to,
            user_pool,
            ..
        } = msg
        else {
            panic!("Invalid message");
        };

        let token_0_creator_chain_id = runtime
            .borrow_mut()
            .token_creator_chain_id(*token_0)
            .expect("Failed: token creator chain id");
        let token_1_creator_chain_id = if let Some(token_1) = token_1 {
            Some(
                runtime
                    .borrow_mut()
                    .token_creator_chain_id(*token_1)
                    .expect("Failed: token creator chain id"),
            )
        } else {
            None
        };

        Self {
            _state: state,
            runtime,

            creator: *creator,
            pool_bytecode_id: *pool_bytecode_id,
            token_0_creator_chain_id,
            token_0: *token_0,
            token_1_creator_chain_id,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            virtual_initial_liquidity: *virtual_initial_liquidity,
            to: *to,
            user_pool: *user_pool,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage> for CreatePoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        log::info!("DEBUG MSG:SWAP: creating pool ...");

        // Run on pool chain
        let application_id = self.runtime.borrow_mut().application_id();
        let chain_id = self.runtime.borrow_mut().chain_id();
        let late_add_liquidity = self.user_pool;

        let pool_application_id = self
            .runtime
            .borrow_mut()
            .create_application::<PoolAbi, PoolParameters, PoolInstantiationArgument>(
                self.pool_bytecode_id,
                &PoolParameters {
                    creator: self.creator,
                    token_0: self.token_0,
                    token_1: self.token_1,
                    virtual_initial_liquidity: self.virtual_initial_liquidity,
                    token_0_creator_chain_id: self.token_0_creator_chain_id,
                    token_1_creator_chain_id: self.token_1_creator_chain_id,
                },
                &PoolInstantiationArgument {
                    amount_0: if late_add_liquidity {
                        Amount::ZERO
                    } else {
                        self.amount_0
                    },
                    amount_1: if late_add_liquidity {
                        Amount::ZERO
                    } else {
                        self.amount_1
                    },
                    pool_fee_percent_mul_100: 30,
                    protocol_fee_percent_mul_100: 5,
                    router_application_id: application_id,
                },
            )
            .forget_abi();

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let pool_application = Account {
            chain_id,
            owner: AccountOwner::from(pool_application_id),
        };
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::PoolCreated {
                creator: self.creator,
                pool_application,
                token_0: self.token_0,
                token_1: self.token_1,
                amount_0: self.amount_0,
                amount_1: self.amount_1,
                virtual_initial_liquidity: self.virtual_initial_liquidity,
                to: self.to,
                user_pool: self.user_pool,
            },
        );

        Ok(Some(outcome))
    }
}
