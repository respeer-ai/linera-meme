use crate::{interfaces::state::StateInterface, FundStatus};
use abi::swap::pool::PoolMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct FundFailHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    transfer_id: u64,
    error: String,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    FundFailHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::FundFail { transfer_id, error } = msg else {
            panic!("Invalid message");
        };

        // It's not safe here to get creator chain id from meme application so we have to pass and record it

        Self {
            state: Rc::new(RefCell::new(state)),
            _runtime: runtime,

            transfer_id: *transfer_id,
            error: error.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage> for FundFailHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        let mut fund_request = self
            .state
            .borrow()
            .fund_request(self.transfer_id)
            .await
            .map_err(Into::into)?;

        fund_request.status = FundStatus::Fail;
        fund_request.error = Some(self.error.clone());

        self.state
            .borrow_mut()
            .update_fund_request(self.transfer_id, fund_request)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
