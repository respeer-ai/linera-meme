use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Amount, ChainOwnership, TimeoutConfig};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct OpenMultiLeaderRoundsHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    OpenMultiLeaderRoundsHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>) -> Self {
        Self { state, runtime }
    }

    fn should_open_multi_leader_rounds(&self) -> bool {
        let enable_mining = self.runtime.borrow_mut().enable_mining();
        let mining_supply = self.runtime.borrow_mut().mining_supply();

        enable_mining
            && matches!(
                mining_supply,
                Some(supply) if supply > Amount::ZERO
            )
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for OpenMultiLeaderRoundsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        if !self.should_open_multi_leader_rounds() {
            return Ok(None);
        }

        let mut ownership =
            ChainOwnership::multiple(Vec::new(), u32::MAX, TimeoutConfig::default());
        ownership.open_multi_leader_rounds = true;

        let chain_id = self.runtime.borrow_mut().chain_id();
        let application_id = self.runtime.borrow_mut().application_id();
        log::info!(
            "open multi leader rounds for chain {}, application {}",
            chain_id,
            application_id,
        );

        match self.runtime.borrow_mut().change_ownership(ownership) {
            Ok(_) => {}
            Err(e) => return Err(HandlerError::RuntimeError(e.into())),
        }

        // Now we don't have any owner, so we can start mining
        self.state.borrow_mut().start_mining();

        Ok(None)
    }
}
