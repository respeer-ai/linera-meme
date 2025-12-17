use std::{cell::RefCell, rc::Rc};

use super::errors::StateError;
use crate::{interfaces::state::StateInterface, state::BlobGatewayState};
use abi::blob_gateway::BlobData;
use async_trait::async_trait;

pub struct StateAdapter {
    state: Rc<RefCell<BlobGatewayState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<BlobGatewayState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = StateError;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error> {
        self.state.borrow_mut().create_blob(blob_data).await
    }
}
