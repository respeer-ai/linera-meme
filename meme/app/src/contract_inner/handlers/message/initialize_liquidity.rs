use crate::{
    contract_inner::handlers::open_multi_leader_rounds::OpenMultiLeaderRoundsHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface + Clone,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    caller: Account,
    pool_application: Account,
    amount_0: Amount,
}

impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface,
        S: StateInterface + Clone,
    > InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
        let MemeMessage::InitializeLiquidity {
            caller,
            pool_application,
            amount_0,
            ..
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            caller: *caller,
            pool_application: *pool_application,
            amount_0: *amount_0,
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface,
        S: StateInterface + Clone,
    > Handler<MemeMessage, MemeResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        assert!(
            self.caller.chain_id == self.runtime.borrow_mut().swap_creator_chain_id(),
            "Invalid caller"
        );
        let swap_application_id = self
            .state
            .swap_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?
            .expect("Swap application not initialized");
        assert!(
            self.caller.owner == AccountOwner::from(swap_application_id),
            "Invalid caller"
        );

        let from = self.runtime.borrow_mut().application_creation_account();
        self.state
            .transfer_from(self.caller, from, self.pool_application, self.amount_0)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        OpenMultiLeaderRoundsHandler::new(self.runtime.clone(), self.state.clone())
            .handle()
            .await?;

        Ok(None)
    }
}
