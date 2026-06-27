use std::sync::Arc;

use crate::interfaces::service::StateServiceInterface;
use abi::state::StateAbi;
use abi::state::StateValue;
use async_graphql::{Request, Response, Variables};
use linera_sdk::serde_json::{self, json};
use linera_sdk::{bcs, linera_base_types::ApplicationId, Service, ServiceRuntime};
use serde::Serialize;
use thiserror::Error;

const READ_QUERY: &str = "query($namespace: Int!, $applicationId: ApplicationId!, $key: [Int!]!) { read(namespace: $namespace, applicationId: $applicationId, key: $key) }";
const BATCH_READ_QUERY: &str = "query($namespace: Int!, $applicationId: ApplicationId!, $keys: [[Int!]!]!) { batchRead(namespace: $namespace, applicationId: $applicationId, keys: $keys) }";

#[derive(Debug, Error)]
pub enum StateServiceError {
    #[error(transparent)]
    Bcs(#[from] bcs::Error),

    #[error(transparent)]
    Json(#[from] serde_json::Error),

    #[error("invalid state service response")]
    InvalidStateServiceResponse,
}

pub struct StateServiceAdapter<S: Service> {
    runtime: Arc<ServiceRuntime<S>>,
    state_app_id: ApplicationId,
    namespace: u8,
}

impl<S: Service> StateServiceAdapter<S> {
    pub fn new(
        runtime: Arc<ServiceRuntime<S>>,
        state_app_id: ApplicationId,
        namespace: u8,
    ) -> Self {
        Self {
            runtime,
            state_app_id,
            namespace,
        }
    }

    fn key_bytes<K: Serialize>(key: &K) -> Result<Vec<u8>, StateServiceError> {
        Ok(bcs::to_bytes(key)?)
    }

    fn query_state_application(&self, request: &Request) -> Response {
        self.runtime
            .query_application(self.state_app_id.with_abi::<StateAbi>(), request)
    }

    fn read_bytes<K: Serialize>(&self, key: &K) -> Result<Option<Vec<u8>>, StateServiceError> {
        let request = Request::new(READ_QUERY).variables(Variables::from_json(json!({
            "namespace": self.namespace,
            "applicationId": self.runtime.application_id().forget_abi(),
            "key": Self::key_bytes(key)?,
        })));
        Self::decode_read_response(self.query_state_application(&request))
    }

    fn batch_read_bytes<K: Serialize>(
        &self,
        keys: &[K],
    ) -> Result<Vec<Option<Vec<u8>>>, StateServiceError> {
        if keys.is_empty() {
            return Ok(Vec::new());
        }
        let keys = keys
            .iter()
            .map(Self::key_bytes)
            .collect::<Result<Vec<_>, _>>()?;
        let request = Request::new(BATCH_READ_QUERY).variables(Variables::from_json(json!({
            "namespace": self.namespace,
            "applicationId": self.runtime.application_id().forget_abi(),
            "keys": keys,
        })));
        Self::decode_batch_read_response(self.query_state_application(&request))
    }

    fn decode_read_response(response: Response) -> Result<Option<Vec<u8>>, StateServiceError> {
        let data = response.data.into_json()?;
        let Some(value) = data.get("read").cloned() else {
            return Err(StateServiceError::InvalidStateServiceResponse);
        };
        Ok(serde_json::from_value(value)?)
    }

    fn decode_batch_read_response(
        response: Response,
    ) -> Result<Vec<Option<Vec<u8>>>, StateServiceError> {
        let data = response.data.into_json()?;
        let Some(value) = data.get("batchRead").cloned() else {
            return Err(StateServiceError::InvalidStateServiceResponse);
        };
        Ok(serde_json::from_value(value)?)
    }
}

impl<S: Service> StateServiceInterface for StateServiceAdapter<S> {
    type Error = StateServiceError;

    fn read<K, V>(&self, key: &K) -> Result<Option<V>, Self::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        self.read_bytes(key)?
            .map(|value| V::from_state_bytes(&value).map_err(StateServiceError::from))
            .transpose()
    }

    fn batch_read<K, V>(&self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        self.batch_read_bytes(keys)?
            .into_iter()
            .map(|value| {
                value
                    .map(|value| V::from_state_bytes(&value).map_err(StateServiceError::from))
                    .transpose()
            })
            .collect()
    }
}
