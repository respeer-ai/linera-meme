use crate::interfaces::state::StateInterface;
use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    proxy::{ProxyAbi, ProxyMessage, ProxyResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{ApplicationId, ApplicationPermissions, ModuleId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreateMemeExtHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    bytecode_id: ModuleId,
    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateMemeExtHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::CreateMemeExt {
            bytecode_id,
            instantiation_argument,
            parameters,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            _state: state,
            runtime,

            bytecode_id: *bytecode_id,
            instantiation_argument: instantiation_argument.clone(),
            parameters: parameters.clone(),
        }
    }

    fn create_meme_application(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> ApplicationId {
        // It should be always run on target chain
        self.runtime
            .borrow_mut()
            .create_application::<ProxyAbi, MemeParameters, MemeInstantiationArgument>(
                bytecode_id,
                &parameters,
                &instantiation_argument,
            )
            .forget_abi()
    }

    fn on_meme_chain_msg_create_meme(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    ) -> HandlerOutcome<ProxyMessage, ProxyResponse> {
        // 1: Create meme application
        let application_id =
            self.create_meme_application(bytecode_id, instantiation_argument, parameters);

        let permissions = ApplicationPermissions {
            execute_operations: Some(vec![application_id]),
            // Don't mandatory any application
            mandatory_applications: vec![],
            close_chain: vec![application_id],
            change_application_permissions: vec![application_id],
            call_service_as_oracle: Some(vec![application_id]),
            make_http_requests: Some(vec![application_id]),
        };
        self.runtime
            .borrow_mut()
            .change_application_permissions(permissions)
            .expect("Failed change application permissions");

        // We're now on meme chain, notify proxy creation chain to store token info
        let meme_chain_id = self.runtime.borrow_mut().chain_id();
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            ProxyMessage::MemeCreated {
                chain_id: meme_chain_id,
                token: application_id,
            },
        );

        outcome
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for CreateMemeExtHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        Ok(Some(self.on_meme_chain_msg_create_meme(
            self.bytecode_id,
            self.instantiation_argument.clone(),
            self.parameters.clone(),
        )))
    }
}
