use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme::{MemeMessage, MemeOperation, MemeResponse},
    swap::pool::PoolInitializeLiquidityCall,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    pool_application: Account,
    amount_0: Amount,
    pool_initialize: PoolInitializeLiquidityCall,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, op: &MemeOperation) -> Self {
        let MemeOperation::InitializeLiquidity {
            pool_application,
            amount_0,
            pool_initialize,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            pool_application: *pool_application,
            amount_0: *amount_0,
            pool_initialize: *pool_initialize,
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<MemeMessage, MemeResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let swap_creator_chain_id = self.runtime.borrow_mut().swap_creator_chain_id();
        assert!(
            chain_id == swap_creator_chain_id,
            "Invalid initialize liquidity chain"
        );
        let caller_id = self
            .runtime
            .borrow_mut()
            .authenticated_caller_id()
            .expect("Invalid initialize liquidity caller");
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        outcome.with_message(
            destination,
            MemeMessage::InitializeLiquidity {
                caller,
                pool_application: self.pool_application,
                amount_0: self.amount_0,
                pool_initialize: self.pool_initialize,
            },
        );

        Ok(Some(outcome))
    }
}
