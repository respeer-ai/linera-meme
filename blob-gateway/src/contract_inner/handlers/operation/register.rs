use crate::interfaces::state::StateInterface;
use abi::{
    blob_gateway::{BlobData, BlobDataType, BlobGatewayMessage, BlobGatewayOperation},
    store_type::StoreType,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::CryptoHash;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RegisterHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    store_type: StoreType,
    data_type: BlobDataType,
    blob_hash: CryptoHash,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &BlobGatewayOperation) -> Self {
        let BlobGatewayOperation::Register {
            store_type,
            data_type,
            blob_hash,
        } = op;

        Self {
            _state: state,
            runtime,

            store_type: *store_type,
            data_type: *data_type,
            blob_hash: *blob_hash,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<BlobGatewayMessage>
    for RegisterHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<BlobGatewayMessage>>, HandlerError> {
        let creator = self.runtime.borrow_mut().authenticated_account();
        let created_at = self.runtime.borrow_mut().system_time();

        let blob_data = BlobData {
            store_type: self.store_type,
            data_type: self.data_type,
            blob_hash: self.blob_hash,
            creator,
            created_at,
        };

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(destination, BlobGatewayMessage::Register { blob_data });

        Ok(Some(outcome))
    }
}
