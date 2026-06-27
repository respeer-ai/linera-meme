use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::AmsState};
use abi::{
    ams::{AmsKey, InstantiationArgument, Metadata, APPLICATION_TYPES},
    application_base_state::StateApplicationIdStorage,
    namespace,
    state::BatchWrite,
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::contract::ContractRuntimeContext;
use state::{adapters::contract::StateContract, interfaces::contract::StateContractInterface};

use super::StateError;

pub struct ContractStateAdapter<R: ContractRuntimeContext> {
    runtime_context: Rc<RefCell<R>>,
    state: Rc<RefCell<AmsState>>,
}

impl<R: ContractRuntimeContext> ContractStateAdapter<R> {
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<AmsState>>) -> Self {
        Self {
            runtime_context,
            state,
        }
    }

    fn state_application(&self) -> Result<StateContract<R>, StateError> {
        let state_application_id = self.state.borrow().get_state_application_id()?;
        Ok(StateContract::new(
            self.runtime_context.clone(),
            state_application_id,
            namespace::AMS,
        ))
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn instantiate(
        &mut self,
        owner: Account,
        argument: InstantiationArgument,
    ) -> Result<(), Self::Error> {
        let state_application_id = argument.state_app_id;
        self.state
            .borrow_mut()
            .set_state_application_id(state_application_id);

        let mut state_application = StateContract::new(
            self.runtime_context.clone(),
            state_application_id,
            namespace::AMS,
        );
        state_application.initialize_operator().await?;
        state_application.create_namespace().await?;
        let application_types = APPLICATION_TYPES
            .iter()
            .map(|application_type| application_type.to_string())
            .collect::<Vec<_>>();
        let mut batch = BatchWrite::new();
        batch.put(&AmsKey::Operator, &owner)?;
        batch.put(&AmsKey::ApplicationTypes, &application_types)?;
        batch.put(&AmsKey::ApplicationIds, &Vec::<ApplicationId>::new())?;
        state_application.batch_write(batch).await?;
        Ok(())
    }

    async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), Self::Error> {
        let mut state_application = self.state_application()?;
        let operator = state_application
            .read::<_, Account>(&AmsKey::Operator)
            .await?
            .ok_or(StateError::NotExists)?;
        if operator != owner {
            return Err(StateError::PermissionDenied);
        }

        let mut application_types = state_application
            .read::<_, Vec<String>>(&AmsKey::ApplicationTypes)
            .await?
            .ok_or(StateError::NotExists)?;
        if application_types.contains(&application_type) {
            return Err(StateError::AlreadyExists);
        }
        application_types.push(application_type);
        state_application
            .write(&AmsKey::ApplicationTypes, &application_types)
            .await?;
        Ok(())
    }

    async fn register_application(&mut self, application: Metadata) -> Result<(), Self::Error> {
        let mut state_application = self.state_application()?;
        let application_types = state_application
            .read::<_, Vec<String>>(&AmsKey::ApplicationTypes)
            .await?
            .ok_or(StateError::NotExists)?;
        if !application_types.contains(&application.application_type) {
            return Err(StateError::InvalidApplicationType);
        }

        let application_id = application.application_id;
        let key = AmsKey::Application { application_id };
        if state_application.read::<_, Metadata>(&key).await?.is_some() {
            return Err(StateError::AlreadyExists);
        }

        let mut application_ids = state_application
            .read::<_, Vec<ApplicationId>>(&AmsKey::ApplicationIds)
            .await?
            .unwrap_or_default();
        if !application_ids.contains(&application_id) {
            application_ids.push(application_id);
        }

        let mut batch = BatchWrite::new();
        batch.put(&key, &application)?;
        batch.put(&AmsKey::ApplicationIds, &application_ids)?;
        state_application.batch_write(batch).await?;
        Ok(())
    }

    async fn claim_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        let mut state_application = self.state_application()?;
        let key = AmsKey::Application { application_id };
        let Some(mut application) = state_application.read::<_, Metadata>(&key).await? else {
            return Err(StateError::NotExists);
        };
        if application.creator.owner != owner.owner {
            return Err(StateError::PermissionDenied);
        }
        application.creator = owner;
        state_application.write(&key, &application).await?;
        Ok(())
    }

    async fn update_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error> {
        let mut state_application = self.state_application()?;
        let key = AmsKey::Application { application_id };
        let Some(existing) = state_application.read::<_, Metadata>(&key).await? else {
            return Err(StateError::NotExists);
        };
        if existing.creator.owner != owner.owner {
            return Err(StateError::PermissionDenied);
        }
        if metadata.application_id != application_id {
            return Err(StateError::PermissionDenied);
        }

        let application_types = state_application
            .read::<_, Vec<String>>(&AmsKey::ApplicationTypes)
            .await?
            .ok_or(StateError::NotExists)?;
        if !application_types.contains(&metadata.application_type) {
            return Err(StateError::InvalidApplicationType);
        }

        let mut updated = metadata;
        updated.creator = existing.creator;
        updated.application_id = existing.application_id;
        updated.created_at = existing.created_at;
        state_application.write(&key, &updated).await?;
        Ok(())
    }
}
