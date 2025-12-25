use crate::interfaces::state::StateInterface;
use abi::{
    meme::{MemeAbi, MemeOperation, MemeResponse},
    swap::pool::{InstantiationArgument, PoolAbi, PoolMessage, PoolParameters},
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

pub struct RequestFundHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    token: ApplicationId,
    transfer_id: u64,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    RequestFundHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::RequestFund {
            token,
            transfer_id,
            amount,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            token: *token,
            transfer_id: *transfer_id,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage> for RequestFundHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        let call = MemeOperation::TransferToCaller {
            amount: self.amount,
        };

        let destination = self
            .runtime
            .borrow_mut()
            .require_message_origin_chain_id()
            .expect("Failed: require message origin chain id");

        let mut outcome = HandlerOutcome::new();

        match self
            .runtime
            .borrow_mut()
            .call_application(self.token.with_abi::<MemeAbi>(), &call)
        {
            MemeResponse::Ok => {
                outcome.with_message(
                    destination,
                    PoolMessage::FundSuccess {
                        transfer_id: self.transfer_id,
                    },
                );
            }
            MemeResponse::Fail(error) => {
                outcome.with_message(
                    destination,
                    PoolMessage::FundFail {
                        transfer_id: self.transfer_id,
                        error,
                    },
                );
            }
            _ => panic!("Invalid response"),
        }

        Ok(Some(outcome))
    }
}
