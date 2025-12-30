use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct FundPoolApplicationCreationChainHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    amount: Amount,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > FundPoolApplicationCreationChainHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, amount: Amount) -> Self {
        Self {
            _state: state,
            runtime,

            amount,
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for FundPoolApplicationCreationChainHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let application = self.runtime.borrow_mut().application_creation_account();

        self.runtime
            .borrow_mut()
            .transfer_combined(None, application, self.amount);

        Ok(None)
    }
}
