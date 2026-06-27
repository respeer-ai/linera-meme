use crate::interfaces::contract::StateContractInterface;
use abi::state::{BatchWrite, StateAbi, StateOperation, StateResponse, StateValue};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::contract::ContractRuntimeContext;
use serde::Serialize;
use std::{cell::RefCell, rc::Rc};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateContractError {
    #[error(transparent)]
    Bcs(#[from] bcs::Error),

    #[error(transparent)]
    Runtime(Box<dyn std::error::Error>),

    #[error("invalid state response")]
    InvalidStateResponse,
}

pub struct StateContract<R: ContractRuntimeContext> {
    runtime: Rc<RefCell<R>>,
    state_app_id: ApplicationId,
    namespace: u8,
}

impl<R: ContractRuntimeContext> StateContract<R> {
    pub fn new(runtime: Rc<RefCell<R>>, state_app_id: ApplicationId, namespace: u8) -> Self {
        Self {
            runtime,
            state_app_id,
            namespace,
        }
    }

    fn call_state(&mut self, operation: StateOperation) -> StateResponse {
        self.runtime
            .borrow_mut()
            .call_application(self.state_app_id.with_abi::<StateAbi>(), &operation)
    }

    fn call_ok(&mut self, operation: StateOperation) -> Result<(), StateContractError> {
        match self.call_state(operation) {
            StateResponse::Ok => Ok(()),
            _ => Err(StateContractError::InvalidStateResponse),
        }
    }

    fn application_id(&mut self) -> ApplicationId {
        self.runtime.borrow_mut().application_id()
    }

    fn authenticated_account(&mut self) -> Account {
        self.runtime.borrow_mut().authenticated_account()
    }

    fn key_bytes<K: Serialize>(key: &K) -> Result<Vec<u8>, StateContractError> {
        Ok(bcs::to_bytes(key)?)
    }

    fn read_bytes<K: Serialize>(&mut self, key: &K) -> Result<Option<Vec<u8>>, StateContractError> {
        let key = Self::key_bytes(key)?;
        match self.call_state(StateOperation::Read {
            namespace: self.namespace,
            key,
        }) {
            StateResponse::Read(value) => Ok(value),
            _ => Err(StateContractError::InvalidStateResponse),
        }
    }

    fn batch_read_bytes<K: Serialize>(
        &mut self,
        keys: &[K],
    ) -> Result<Vec<Option<Vec<u8>>>, StateContractError> {
        let keys = keys
            .iter()
            .map(Self::key_bytes)
            .collect::<Result<Vec<_>, _>>()?;

        match self.call_state(StateOperation::BatchRead {
            namespace: self.namespace,
            keys,
        }) {
            StateResponse::BatchRead(values) => Ok(values),
            _ => Err(StateContractError::InvalidStateResponse),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateContractInterface for StateContract<R> {
    type Error = StateContractError;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error> {
        let operator = self.authenticated_account();
        self.call_ok(StateOperation::InitializeOperator { operator })
    }

    async fn create_namespace(&mut self) -> Result<(), Self::Error> {
        self.call_ok(StateOperation::CreateNamespace {
            namespace: self.namespace,
        })
    }

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error> {
        let application_id = self.application_id();
        self.call_ok(StateOperation::FreezeNamespace { application_id })
    }

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error> {
        let application_id = self.application_id();
        self.call_ok(StateOperation::UnfreezeNamespace { application_id })
    }

    async fn handoff(&mut self, new_application_id: ApplicationId) -> Result<(), Self::Error> {
        let application_id = self.application_id();
        self.call_ok(StateOperation::Handoff {
            application_id,
            namespace: self.namespace,
            new_application_id,
        })
    }

    async fn read<K, V>(&mut self, key: &K) -> Result<Option<V>, Self::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        self.read_bytes(key)?
            .map(|value| V::from_state_bytes(&value).map_err(StateContractError::from))
            .transpose()
    }

    async fn batch_read<K, V>(&mut self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        self.batch_read_bytes(keys)?
            .into_iter()
            .map(|value| {
                value
                    .map(|value| V::from_state_bytes(&value).map_err(StateContractError::from))
                    .transpose()
            })
            .collect()
    }

    async fn write<K, V>(&mut self, key: &K, value: &V) -> Result<(), Self::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        let key = Self::key_bytes(key)?;
        let value = value.into_state_bytes()?;
        self.call_ok(StateOperation::Write {
            namespace: self.namespace,
            key,
            value,
        })
    }

    async fn batch_write(&mut self, batch: BatchWrite) -> Result<(), Self::Error> {
        let writes = batch.into_writes();
        if !writes.is_empty() {
            self.call_ok(StateOperation::BatchWrite {
                namespace: self.namespace,
                writes,
            })?;
        }

        Ok(())
    }

    async fn delete<K>(&mut self, key: &K) -> Result<(), Self::Error>
    where
        K: Serialize,
    {
        let key = Self::key_bytes(key)?;
        self.call_ok(StateOperation::Delete {
            namespace: self.namespace,
            key,
        })
    }
}
