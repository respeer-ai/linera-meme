use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::pool::{Pool, PoolInitializeArgument, PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    argument: PoolInitializeArgument,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    InitializeHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::Initialize { argument } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            argument: argument.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for InitializeHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        // Only the swap application that created this pool may initialize it,
        // ensuring initialization happens exactly once as part of the atomic
        // create flow. The router application id is supplied by the caller and
        // is also stored as the pool's router.
        if caller != self.argument.router_application_id {
            return Err(HandlerError::NotAllowed);
        }
        let creator = self.runtime.borrow_mut().creator();
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();
        let block_timestamp = self.runtime.borrow_mut().system_time();
        let pool = Pool::create(
            token_0,
            token_1,
            self.argument.pool_fee_percent_mul_100,
            creator,
            block_timestamp,
        );

        self.state
            .initialize(pool, self.argument.router_application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(PoolResponse::Ok);
        Ok(Some(outcome))
    }
}
