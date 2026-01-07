use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse, MiningBase};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::CryptoHash;
use num_bigint::BigUint;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, cmp::Ordering, rc::Rc};

pub struct MineHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    nonce: CryptoHash,
}

fn hash_to_u256(hash: CryptoHash) -> BigUint {
    BigUint::from_bytes_be(&hash.as_bytes().0)
}

fn hash_cmp(hash1: CryptoHash, hash2: CryptoHash) -> Ordering {
    let hash1_bigint = hash_to_u256(hash1);
    let hash2_bigint = hash_to_u256(hash2);

    hash1_bigint.cmp(&hash2_bigint)
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    MineHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
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
        let mined_height = self.state.mining_height();

        assert!(height > mined_height, "Stale block height");

        let chain_id = self.runtime.borrow_mut().chain_id();
        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        let previous_nonce = self.state.previous_nonce();

        let mining_base = MiningBase {
            height,
            nonce: self.nonce,
            chain_id,
            signer,
            previous_nonce,
        };

        let hash = CryptoHash::new(&mining_base);
        let mining_target = self.state.mining_target();

        match hash_cmp(hash, mining_target) {
            Ordering::Less => {}
            Ordering::Equal => {}
            Ordering::Greater => return Err(HandlerError::ProcessError("Invalid nonce".into())),
        }

        let mut mining_info = self.state.mining_info();

        mining_info.mining_height = height;
        mining_info.previous_nonce = self.nonce;

        self.state.update_mining_info(mining_info);

        Ok(())
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
        // TODO: calculate reward according to operations and messages
        // TODO: distribute reward to block proposer
        // TODO: adjust target according to block time duration

        // TODO: if the height is already mine, fail it

        self.verify()?;

        Ok(None)
    }
}
