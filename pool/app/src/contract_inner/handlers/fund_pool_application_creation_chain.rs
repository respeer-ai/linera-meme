use crate::interfaces::state::StateInterface;
use abi::pool::{PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct FundPoolApplicationCreationChainHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + Clone,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + Clone>
    FundPoolApplicationCreationChainHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, amount: Amount) -> Self {
        Self {
            runtime,
            _state: state,
            amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + Clone>
    Handler<PoolMessage, PoolResponse> for FundPoolApplicationCreationChainHandler<R, S>
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
