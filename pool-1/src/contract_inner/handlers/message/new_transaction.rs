use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::{
    pool::PoolMessage,
    router::{SwapAbi, SwapOperation},
    transaction::Transaction,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct NewTransactionHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    transaction: Transaction,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    NewTransactionHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::NewTransaction { transaction } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            transaction: *transaction,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<PoolMessage> for NewTransactionHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        let transaction = self.state.create_transaction(self.transaction);
        let (token_0_price, token_1_price) = self.state.calculate_price_pair();
        let reserve_0 = self.state.reserve_0();
        let reserve_1 = self.state.reserve_1();

        let call = SwapOperation::UpdatePool {
            token_0: self.runtime.borrow_mut().token_0(),
            token_1: self.runtime.borrow_mut().token_1(),
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        };
        let _ = self.runtime.borrow_mut().call_application(
            self.state.router_application_id().with_abi::<SwapAbi>(),
            &call,
        );
        Ok(None)
    }
}
