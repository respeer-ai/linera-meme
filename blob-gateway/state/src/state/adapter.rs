use std::{cell::RefCell, rc::Rc};

use abi::blob_gateway::{state_v1::StateInstantiationArgument, BlobData};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId, CryptoHash};

use crate::{interfaces::state::StateInterface, state::BlobGatewayStateV1};

pub struct StateAdapter {
    state: Rc<RefCell<BlobGatewayStateV1>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<BlobGatewayStateV1>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = <BlobGatewayStateV1 as StateInterface>::Error;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state.borrow_mut().instantiate(argument);
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.state.borrow_mut().business_application_id().await
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_operator(new_operator).await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(new_business_application_id)
            .await
    }

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error> {
        self.state.borrow_mut().create_blob(blob_data).await
    }

    async fn blob(&mut self, blob_hash: CryptoHash) -> Result<Option<BlobData>, Self::Error> {
        self.state.borrow_mut().blob(blob_hash).await
    }

    async fn blobs(&mut self) -> Result<Vec<BlobData>, Self::Error> {
        self.state.borrow_mut().blobs().await
    }
}
