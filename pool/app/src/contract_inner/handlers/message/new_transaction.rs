use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::pool::{PoolMessage, PoolResponse, Transaction};
use abi::swap::router::{SwapAbi, SwapOperation};
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

            transaction: transaction.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for NewTransactionHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let pool = self
            .state
            .pool()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        let (token_0_price, token_1_price) = pool.calculate_price_pair();
        let reserve_0 = pool.reserve_0;
        let reserve_1 = pool.reserve_1;

        let router_application_id = self
            .state
            .router_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();

        let call = SwapOperation::UpdatePool {
            token_0,
            token_1,
            transaction: self.transaction.clone(),
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        };
        let _ = self.runtime.borrow_mut().call_application(
            router_application_id.with_abi::<SwapAbi>(),
            &call,
        );
        Ok(None)
    }
}
