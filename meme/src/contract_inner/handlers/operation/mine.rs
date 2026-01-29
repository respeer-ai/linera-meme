use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    hash::hash_cmp,
    meme::{MemeMessage, MemeOperation, MemeResponse, MiningBase},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{BlockHeight, CryptoHash};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, cmp::Ordering, rc::Rc};

pub struct MineHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    nonce: CryptoHash,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > MineHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, op: &MemeOperation) -> Self {
        let MemeOperation::Mine { nonce } = op else {
            panic!("Invalid operation");
        };

        Self {
            state,
            runtime,

            nonce: *nonce,
        }
    }

    fn verify(&mut self) -> Result<(), HandlerError> {
        let height = self.runtime.borrow_mut().block_height();
        let mined_height = self.state.borrow().mining_height();

        assert!(
            height >= mined_height,
            "Stale block height, expected {}, mined {}",
            height,
            mined_height,
        );

        let chain_id = self.runtime.borrow_mut().chain_id();
        let signer = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .expect("Invalid signer");
        let previous_nonce = self.state.borrow().previous_nonce();

        let mining_base = MiningBase {
            height,
            nonce: self.nonce,
            chain_id,
            signer,
            previous_nonce,
        };

        log::info!("mined {:?}", mining_base);

        let hash = CryptoHash::new(&mining_base);
        let mining_target = self.state.borrow().mining_target();

        match hash_cmp(hash, mining_target) {
            Ordering::Less => {}
            Ordering::Equal => {}
            Ordering::Greater => return Err(HandlerError::ProcessError("Invalid nonce".into())),
        }

        let mut mining_info = self.state.borrow().mining_info();

        mining_info.mining_height = height.saturating_add(BlockHeight(1));
        mining_info.previous_nonce = self.nonce;

        self.state.borrow_mut().update_mining_info(mining_info);

        Ok(())
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<MemeMessage, MemeResponse> for MineHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        // TODO: check first operation of the block must be mine
        // TODO: calculate reward according to operations and messages
        // TODO: distribute reward to block proposer
        // TODO: adjust target according to block time duration

        // TODO: if the height is already mine, fail it

        if !self.runtime.borrow_mut().enable_mining() {
            return Err(HandlerError::NotEnabled);
        }

        self.verify()?;

        let owner = self.runtime.borrow_mut().authenticated_account();
        let now = self.runtime.borrow_mut().system_time();

        self.state
            .borrow_mut()
            .mining_reward(owner, now)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
