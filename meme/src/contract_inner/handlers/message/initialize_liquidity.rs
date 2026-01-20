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
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    caller: Account,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
        let MemeMessage::InitializeLiquidity { caller, to, amount } = msg else {
            panic!("Invalid message");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            caller: *caller,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        assert!(
            self.caller.chain_id == self.runtime.borrow_mut().swap_creator_chain_id(),
            "Invalid caller"
        );
        assert!(
            self.caller.owner
                == AccountOwner::from(self.state.borrow().swap_application_id().unwrap()),
            "Invalid caller"
        );

        let from = self.runtime.borrow_mut().application_creation_account();
        self.state
            .borrow_mut()
            .transfer_from(self.caller, from, self.to, self.amount)
            .await
            .map_err(Into::into)?;

        // This should be the final message of initialization so we change ownership here
        let _ = OpenMultiLeaderRoundsHandler::new(self.runtime.clone(), self.state.clone())
            .handle()
            .await?;

        Ok(None)
    }
}
