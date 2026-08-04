use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    application_state_base::PublicStateBaseInterface,
    meme::{MemeMessage, MemeResponse},
    swap::router::{SwapAbi, SwapOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct LiquidityFundedHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface + PublicStateBaseInterface>
    LiquidityFundedHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
        let MemeMessage::LiquidityFunded = msg else {
            panic!("Invalid message");
        };

        Self { state, runtime }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface + PublicStateBaseInterface>
    Handler<MemeMessage, MemeResponse> for LiquidityFundedHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        log::info!("DEBUG MEME:MSG liquidity funded");

        let virtual_liquidity = self.runtime.borrow_mut().virtual_initial_liquidity();
        // Use the state-app stored liquidity, which has been adjusted for mining supply.
        let Some(liquidity) = self
            .state
            .initial_liquidity()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?
        else {
            return Ok(None);
        };
        let swap_application_id = self
            .state
            .swap_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        let Some(swap_application_id) = swap_application_id else {
            return Ok(None);
        };

        let creator = self.runtime.borrow_mut().creator();
        let chain_id = self.runtime.borrow_mut().chain_id();
        let application_id = self.runtime.borrow_mut().application_id().forget_abi();

        let call = SwapOperation::InitializeLiquidity {
            creator,
            token_0_creator_chain_id: chain_id,
            token_0: application_id,
            amount_0: liquidity.fungible_amount,
            amount_1: liquidity.native_amount,
            virtual_liquidity,
            to: None,
        };
        let _ = self
            .runtime
            .borrow_mut()
            .call_application(swap_application_id.with_abi::<SwapAbi>(), &call);

        Ok(None)
    }
}
