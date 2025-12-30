use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::CryptoHash;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct MineHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    _state: S,

    _nonce: CryptoHash,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    MineHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
        let MemeOperation::Mine { nonce } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            _runtime: runtime,

            _nonce: *nonce,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for MineHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        // TODO: check first operation of the block must be mine
        // TODO: distribute reward to block proposer
        Err(HandlerError::NotImplemented)
    }
}
