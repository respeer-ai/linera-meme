use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{
    interfaces::state::StateInterface, state::errors::StateError, state::State, state_key::StateKey,
};

const MAX_NAMESPACE_SLOTS: usize = u8::MAX as usize + 1;

#[async_trait(?Send)]
impl StateInterface for State {
    type Error = StateError;

    async fn initialize_operator(&mut self, operator: Account) -> Result<(), Self::Error> {
        if self.operator.get().is_some() {
            return Err(StateError::OperatorAlreadyInitialized);
        }

        self.operator.set(Some(operator));
        Ok(())
    }

    async fn create_namespace(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.require_initialized_operator()?;
        self.require_namespace_management_open()?;

        let mut applications = self
            .namespace_apps
            .get(&namespace)
            .await?
            .unwrap_or_default();

        if applications.contains(&application_id) {
            return Err(StateError::ApplicationAlreadyBound(application_id));
        }
        if applications.len() >= MAX_NAMESPACE_SLOTS {
            return Err(StateError::NamespaceFull(namespace));
        }

        applications.push(application_id);
        Ok(self.namespace_apps.insert(&namespace, applications)?)
    }

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error> {
        self.require_initialized_operator()?;
        self.frozen_namespaces.set(true);
        Ok(())
    }

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error> {
        self.require_initialized_operator()?;
        self.frozen_namespaces.set(false);
        Ok(())
    }

    async fn handoff(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.require_initialized_operator()?;
        self.require_namespace_management_open()?;

        let mut applications = self
            .namespace_apps
            .get(&namespace)
            .await?
            .ok_or(StateError::NamespaceNotFound(namespace))?;

        let Some(slot) = applications
            .iter()
            .position(|application| *application == application_id)
        else {
            return Err(StateError::ApplicationNotBound {
                namespace,
                application_id,
            });
        };

        if applications.contains(&new_application_id) {
            return Err(StateError::HandoffTargetAlreadyBound(new_application_id));
        }

        applications[slot] = new_application_id;
        Ok(self.namespace_apps.insert(&namespace, applications)?)
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.require_initialized_operator()?;
        self.require_namespace_management_open()?;
        self.operator.set(Some(new_operator));
        Ok(())
    }

    async fn application_slot(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<u8, Self::Error> {
        self.resolve_application_slot(namespace, application_id)
            .await
    }

    async fn read(&mut self, key: StateKey) -> Result<Option<Vec<u8>>, Self::Error> {
        Ok(self.records.get(&key.into_bytes()).await?)
    }

    async fn write(&mut self, key: StateKey, value: Vec<u8>) -> Result<(), Self::Error> {
        Ok(self.records.insert(&key.into_bytes(), value)?)
    }

    async fn delete(&mut self, key: StateKey) -> Result<(), Self::Error> {
        Ok(self.records.remove(&key.into_bytes())?)
    }

    async fn batch_read(
        &mut self,
        keys: Vec<StateKey>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error> {
        let mut values = Vec::with_capacity(keys.len());

        for key in keys {
            values.push(self.records.get(&key.into_bytes()).await?);
        }

        Ok(values)
    }

    async fn batch_write(&mut self, writes: Vec<(StateKey, Vec<u8>)>) -> Result<(), Self::Error> {
        for (key, value) in writes {
            self.records.insert(&key.into_bytes(), value)?;
        }

        Ok(())
    }

    async fn batch_delete(&mut self, keys: Vec<StateKey>) -> Result<(), Self::Error> {
        for key in keys {
            self.records.remove(&key.into_bytes())?;
        }

        Ok(())
    }
}

impl State {
    fn require_initialized_operator(&self) -> Result<Account, StateError> {
        self.operator
            .get()
            .ok_or(StateError::OperatorNotInitialized)
    }

    fn require_namespace_management_open(&self) -> Result<(), StateError> {
        if *self.frozen_namespaces.get() {
            return Err(StateError::NamespaceManagementFrozen);
        }
        Ok(())
    }

    async fn resolve_application_slot(
        &self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<u8, StateError> {
        let applications = self
            .namespace_apps
            .get(&namespace)
            .await?
            .ok_or(StateError::NamespaceNotFound(namespace))?;

        let Some(slot) = applications
            .iter()
            .position(|application| *application == application_id)
        else {
            return Err(StateError::ApplicationNotBound {
                namespace,
                application_id,
            });
        };

        slot.try_into()
            .map_err(|_| StateError::NamespaceSlotOverflow { namespace, slot })
    }
}
