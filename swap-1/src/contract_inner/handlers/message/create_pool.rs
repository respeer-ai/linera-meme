use crate::interfaces::state::StateInterface;
use abi::swap::SwapMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreatePoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

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

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreatePoolHandler<R, S> {
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
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            creator: *creator,
            pool_bytecode_id: *pool_bytecode_id,
            token_0: *token_0,
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
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<SwapMessage>
    for CreatePoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        log::info!("DEBUG MSG:SWAP: creating pool ...");

        // Run on pool chain
        let application_id = self.runtime.application_id().forget_abi();
        let chain_id = self.runtime.chain_id();
        let late_add_liquidity = user_pool;

        let pool_application_id = self
            .runtime
            .borrow_mut()
            .create_application::<PoolAbi, PoolParameters, PoolInstantiationArgument>(
                pool_bytecode_id,
                &PoolParameters {
                    creator,
                    token_0,
                    token_1,
                    virtual_initial_liquidity,
                    token_0_creator_chain_id,
                    token_1_creator_chain_id,
                },
                &PoolInstantiationArgument {
                    amount_0: if late_add_liquidity {
                        Amount::ZERO
                    } else {
                        amount_0
                    },
                    amount_1: if late_add_liquidity {
                        Amount::ZERO
                    } else {
                        amount_1
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
                creator,
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
                to,
                user_pool,
            },
        );

        Ok(Some(outcome))
    }
}
