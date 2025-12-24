use crate::interfaces::state::StateInterface;
use abi::swap::{SwapMessage, SwapOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    creator: Account,
    token_0: ApplicationId,
    amount_0: Amount,
    amount_1: Amount,
    virtual_liquidity: bool,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &SwapOperation) -> Self {
        let SwapOperation::InitializeLiquidity {
            creator,
            token_0,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            creator: *creator,
            token_0: *token_0,
            amount_0: *amount_0,
            amount_1: *amount_1,
            virtual_liquidity: *virtual_liquidity,
            to: *to,
        }
    }
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    fn formalize_virtual_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        virtual_liquidity: bool,
    ) -> bool {
        if !virtual_liquidity {
            return false;
        }
        if token_1.is_some() {
            return false;
        }

        let Some(caller_application_id) = self.runtime.borrow_mut().authenticated_caller_id()
        else {
            return false;
        };
        if caller_application_id != token_0 {
            return false;
        }

        let token_0_creator_chain_id = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(token_0)
            .expect("Failed: token creator chain id");

        if self.runtime.borrow_mut().chain_id() != token_0_creator_chain_id {
            return false;
        }
        return true;
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage> for InitializeLiquidityHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        log::info!("DEBUG OP:SWAP: calling initialize liquidity ...");

        let caller_id = self
            .runtime
            .borrow_mut()
            .authenticated_caller_id()
            .expect("Invalid caller");
        let chain_id = self.runtime.borrow_mut().chain_id();
        let token_0_creator_chain_id = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(self.token_0)
            .expect("Failed: token creator chain id");

        assert!(self.token_0 == caller_id, "Invalid caller");
        assert!(chain_id == token_0_creator_chain_id, "Invalid caller");

        let virtual_liquidity =
            self.formalize_virtual_liquidity(self.token_0, None, self.virtual_liquidity);

        // Here allowance is already approved, so just transfer native amount then create pool
        // chain and application
        // ATM liquidity fund and fee budget should already deposited to signer of swap chain
        // Meme creator already fund swap chain in meme application so we don't need to charge pool
        // chain open fee here
        // If native liquidity is needed, at that time it's already been deposited to swap application
        // on swap chain

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::InitializeLiquidity {
                creator: self.creator,
                token_0: self.token_0,
                amount_0: self.amount_0,
                amount_1: self.amount_1,
                virtual_liquidity: self.virtual_liquidity,
                to: self.to,
            },
        );

        Ok(Some(outcome))
    }
}
