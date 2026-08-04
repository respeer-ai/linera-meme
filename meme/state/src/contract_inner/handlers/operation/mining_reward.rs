use abi::meme::{MemeStateV1Operation, MemeStateV1Response, MiningInfo};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct MiningRewardHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    reward_amount: Amount,
    mining_info: MiningInfo,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> MiningRewardHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeStateV1Operation) -> Self {
        let MemeStateV1Operation::MiningReward {
            owner,
            reward_amount,
            mining_info,
        } = operation
        else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            owner: *owner,
            reward_amount: *reward_amount,
            mining_info: mining_info.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), MemeStateV1Response>
    for MiningRewardHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let business_application_id = self
            .state
            .business_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        if caller != business_application_id {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .mining_reward(self.owner, self.reward_amount, self.mining_info.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::Ok);
        Ok(Some(outcome))
    }
}
