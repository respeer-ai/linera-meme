use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme::{MemeMessage, MemeResponse},
    swap::router::{SwapAbi, SwapOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct LiquidityFundedHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > LiquidityFundedHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
        let MemeMessage::LiquidityFunded = msg else {
            panic!("Invalid message");
        };

        Self { state, runtime }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<MemeMessage, MemeResponse> for LiquidityFundedHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        log::info!("DEBUG MEME:MSG liquidity funded");

        let virtual_liquidity = self.runtime.borrow_mut().virtual_initial_liquidity();
        let Some(liquidity) = self.runtime.borrow_mut().initial_liquidity() else {
            return Ok(None);
        };
        let Some(swap_application_id) = self.state.swap_application_id() else {
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
