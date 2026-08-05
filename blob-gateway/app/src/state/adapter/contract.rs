use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::BlobGatewayState};
use abi::{
    application_state_base::{LocalStateInterface, PublicStateBaseInterface},
    blob_gateway::{
        state_v1::{
            BlobGatewayStateAbi as BlobGatewayStateV1Abi, BlobGatewayStateV1Operation,
            BlobGatewayStateV1Response,
        },
        BlobData,
    },
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId, CryptoHash};
use runtime::interfaces::contract::ContractRuntimeContext;

use super::StateError;

pub struct ContractStateAdapter<R: ContractRuntimeContext> {
    runtime_context: Rc<RefCell<R>>,
    state: Rc<RefCell<BlobGatewayState>>,
}

impl<R: ContractRuntimeContext> ContractStateAdapter<R> {
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<BlobGatewayState>>) -> Self {
        Self {
            runtime_context,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> PublicStateBaseInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .append_state(state_application_id)
            .await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        let state_applications = self.state.borrow()._state_applications().await?;
        if state_applications.is_empty() {
            return Err(StateError::InvalidStateVersion);
        }
        for (_version, state_application_id) in state_applications {
            let response = self.runtime_context.borrow_mut().call_application(
                state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
                &BlobGatewayStateV1Operation::Handoff {
                    new_business_application_id,
                },
            );
            match response {
                BlobGatewayStateV1Response::Ok => {}
                _ => return Err(StateError::InvalidStateResponse),
            }
        }
        Ok(())
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &BlobGatewayStateV1Operation::SetOperator { new_operator },
        );
        match response {
            BlobGatewayStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &BlobGatewayStateV1Operation::CreateBlob { blob_data },
        );
        match response {
            BlobGatewayStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn blob(&mut self, blob_hash: CryptoHash) -> Result<Option<BlobData>, Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &BlobGatewayStateV1Operation::Blob { blob_hash },
        );
        match response {
            BlobGatewayStateV1Response::Blob(blob) => Ok(blob),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn blobs(&mut self) -> Result<Vec<BlobData>, Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &BlobGatewayStateV1Operation::Blobs,
        );
        match response {
            BlobGatewayStateV1Response::Blobs(blobs) => Ok(blobs),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}
