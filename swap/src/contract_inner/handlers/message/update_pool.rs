use crate::interfaces::state::StateInterface;
use abi::swap::{
    router::{SwapMessage, SwapResponse},
    transaction::Transaction,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdatePoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    transaction: Transaction,
    token_0_price: Amount,
    token_1_price: Amount,
    reserve_0: Amount,
    reserve_1: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdatePoolHandler<R, S> {
    async fn validate_pool_origin_chain(&mut self) {
        let origin = self
            .runtime
            .borrow_mut()
            .require_message_origin_chain_id()
            .expect("Invalid message origin chain");
        let pool = self
            .state
            .get_pool_exchangable(self.token_0, self.token_1)
            .await
            .expect("Failed: get pool exchangable")
            .expect("Invalid pool");

        assert_eq!(
            origin, pool.pool_application.chain_id,
            "Invalid pool origin chain"
        );
    }

    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::UpdatePool {
            token_0,
            token_1,
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,

            token_0: *token_0,
            token_1: *token_1,
            transaction: *transaction,
            token_0_price: *token_0_price,
            token_1_price: *token_1_price,
            reserve_0: *reserve_0,
            reserve_1: *reserve_1,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<SwapMessage, SwapResponse> for UpdatePoolHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<SwapMessage, SwapResponse>>, HandlerError> {
        self.validate_pool_origin_chain().await;

        self.state
            .update_pool(
                self.token_0,
                self.token_1,
                self.transaction,
                self.token_0_price,
                self.token_1_price,
                self.reserve_0,
                self.reserve_1,
            )
            .await
            .expect("Failed: update pool");

        Ok(None)
    }
}
