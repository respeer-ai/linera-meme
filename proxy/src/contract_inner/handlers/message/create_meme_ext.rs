use crate::interfaces::state::StateInterface;
use abi::{
    meme::{
        InitializeArgument, InstantiationArgument as MemeInstantiationArgument, MemeAbi,
        MemeOperation, MemeParameters, MemeResponse, MemeStateAbi, StateInstantiationArgument,
    },
    proxy::{ProxyMessage, ProxyResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{
    Account, Amount, ApplicationId, ApplicationPermissions, ModuleId,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreateMemeExtHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    #[allow(dead_code)]
    state: S,

    bytecode_id: ModuleId,
    state_bytecode_ids: Vec<(u16, ModuleId)>,
    instantiation_argument: MemeInstantiationArgument,
    parameters: MemeParameters,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateMemeExtHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::CreateMemeExt {
            bytecode_id,
            state_bytecode_ids,
            instantiation_argument,
            parameters,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            bytecode_id: *bytecode_id,
            state_bytecode_ids: state_bytecode_ids.clone(),
            instantiation_argument: instantiation_argument.clone(),
            parameters: parameters.clone(),
        }
    }

    fn create_meme_application(
        &mut self,
        bytecode_id: ModuleId,
        instantiation_argument: &MemeInstantiationArgument,
        parameters: &MemeParameters,
    ) -> ApplicationId {
        self.runtime
            .borrow_mut()
            .create_application::<MemeAbi, MemeParameters, MemeInstantiationArgument>(
                bytecode_id,
                parameters,
                instantiation_argument,
            )
            .forget_abi()
    }

    fn create_meme_state_application(
        &mut self,
        business_application_id: ApplicationId,
        bytecode_id: ModuleId,
        operator: Account,
    ) -> ApplicationId {
        let proxy_application_id = self.runtime.borrow_mut().application_id().forget_abi();

        let argument = StateInstantiationArgument {
            business_application_id,
            operator: Some(operator),
            proxy_application_id: Some(proxy_application_id),
        };

        self.runtime
            .borrow_mut()
            .create_application::<MemeStateAbi, (), StateInstantiationArgument>(
                bytecode_id,
                &(),
                &argument,
            )
            .forget_abi()
    }

    fn create_meme_state_applications(
        &mut self,
        business_application_id: ApplicationId,
        operator: Account,
    ) -> Vec<ApplicationId> {
        self.state_bytecode_ids
            .clone()
            .into_iter()
            .map(|(_, bytecode_id)| {
                self.create_meme_state_application(business_application_id, bytecode_id, operator)
            })
            .collect()
    }

    fn append_state_applications(
        &mut self,
        business_application_id: ApplicationId,
        state_application_ids: Vec<ApplicationId>,
    ) -> MemeResponse {
        self.runtime.borrow_mut().call_application(
            business_application_id.with_abi::<MemeAbi>(),
            &MemeOperation::AppendStates {
                state_application_ids,
            },
        )
    }

    fn initialize_meme_application(
        &mut self,
        business_application_id: ApplicationId,
        instantiation_argument: &MemeInstantiationArgument,
        parameters: &MemeParameters,
    ) -> MemeResponse {
        let argument = InitializeArgument {
            owner: parameters.creator,
            holder: parameters.creator,
            meme: instantiation_argument.meme.clone(),
            initial_owner_balance: Amount::ZERO,
            blob_gateway_application_id: instantiation_argument.blob_gateway_application_id,
            ams_application_id: instantiation_argument.ams_application_id,
            swap_application_id: instantiation_argument.swap_application_id,
            enable_mining: parameters.enable_mining,
            mining_supply: parameters.mining_supply,
            now: self.runtime.borrow_mut().system_time(),
        };

        self.runtime.borrow_mut().call_application(
            business_application_id.with_abi::<MemeAbi>(),
            &MemeOperation::Initialize { argument },
        )
    }

    fn restrict_chain_permissions(&mut self, application_id: ApplicationId) {
        let permissions = ApplicationPermissions {
            execute_operations: None,
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
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for CreateMemeExtHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        let bytecode_id = self.bytecode_id;
        let instantiation_argument = self.instantiation_argument.clone();
        let parameters = self.parameters.clone();
        let operator = parameters.creator;

        let business_application_id =
            self.create_meme_application(bytecode_id, &instantiation_argument, &parameters);

        let state_application_ids =
            self.create_meme_state_applications(business_application_id, operator);

        let response =
            self.append_state_applications(business_application_id, state_application_ids);
        assert!(
            matches!(response, MemeResponse::Ok),
            "Failed to append meme state applications"
        );

        let response = self.initialize_meme_application(
            business_application_id,
            &instantiation_argument,
            &parameters,
        );
        assert!(
            matches!(response, MemeResponse::Ok),
            "Failed to initialize meme application"
        );

        self.restrict_chain_permissions(business_application_id);

        let meme_chain_id = self.runtime.borrow_mut().chain_id();
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            ProxyMessage::MemeCreated {
                chain_id: meme_chain_id,
                token: business_application_id,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
