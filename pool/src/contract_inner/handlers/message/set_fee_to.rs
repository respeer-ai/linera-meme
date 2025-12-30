use crate::interfaces::state::StateInterface;
use abi::swap::pool::{PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct SetFeeToHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    operator: Account,
    account: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> SetFeeToHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::SetFeeTo { operator, account } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            operator: *operator,
            account: *account,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for SetFeeToHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        self.state.set_fee_to(self.operator, self.account);
        Ok(None)
    }
}
