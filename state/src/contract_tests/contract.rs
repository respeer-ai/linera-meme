use abi::state::{StateAbi, StateBaseInterface, StateOperation, StateResponse};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, BlockHeight, ChainId,
        ChainOwnership, ChangeApplicationPermissionsError, ChangeOwnershipError, CryptoHash,
        ModuleId, Timestamp,
    },
};
use runtime::interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext};
use serde::{Deserialize, Serialize};
use state::{
    adapters::contract::{StateContract, StateContractError},
    interfaces::contract::StateContractInterface,
};
use std::{cell::RefCell, error::Error, fmt, rc::Rc, str::FromStr};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
enum ExampleBusinessKey {
    Counter,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
struct ExampleCounter {
    value: u64,
}

struct ExampleBusinessHandler<S> {
    state: S,
}

impl<S> ExampleBusinessHandler<S>
where
    S: StateContractInterface,
{
    fn new(state: S) -> Self {
        Self { state }
    }

    async fn increment_counter(&mut self) -> Result<ExampleCounter, S::Error> {
        let key = ExampleBusinessKey::Counter;
        let mut counter = self
            .state
            .read::<_, ExampleCounter>(&key)
            .await?
            .unwrap_or(ExampleCounter { value: 0 });
        counter.value += 1;
        self.state.write(&key, &counter).await?;
        Ok(counter)
    }
}

fn build_example_handler_at_entry_layer<R>(
    runtime: Rc<RefCell<R>>,
) -> Result<ExampleBusinessHandler<StateContract<R>>, StateContractError>
where
    R: ContractRuntimeContext + StateBaseInterface,
{
    let state = StateContract::new(runtime)?;
    Ok(ExampleBusinessHandler::new(state))
}

#[derive(Debug, Eq, PartialEq)]
enum StateCall {
    StateAppId,
    StateNamespace,
    Read {
        application_id: ApplicationId,
        namespace: u8,
        key: Vec<u8>,
    },
    Write {
        application_id: ApplicationId,
        namespace: u8,
        key: Vec<u8>,
        value: Vec<u8>,
    },
}

#[derive(Debug)]
struct MockRuntimeError;

impl fmt::Display for MockRuntimeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("mock runtime error")
    }
}

impl Error for MockRuntimeError {}

struct MockRuntime {
    state_app_id: ApplicationId,
    namespace: u8,
    counter: Option<ExampleCounter>,
    calls: Vec<StateCall>,
}

impl MockRuntime {
    fn new(state_app_id: ApplicationId, namespace: u8) -> Self {
        Self {
            state_app_id,
            namespace,
            counter: None,
            calls: Vec::new(),
        }
    }
}

impl StateBaseInterface for MockRuntime {
    type Error = MockRuntimeError;

    fn state_app_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.calls.push(StateCall::StateAppId);
        Ok(self.state_app_id)
    }

    fn state_namespace(&mut self) -> Result<u8, Self::Error> {
        self.calls.push(StateCall::StateNamespace);
        Ok(self.namespace)
    }
}

impl BaseRuntimeContext for MockRuntime {
    type Parameters = ();

    fn chain_id(&mut self) -> ChainId {
        chain_id()
    }

    fn system_time(&mut self) -> Timestamp {
        Timestamp::from(1)
    }

    fn application_creator_chain_id(&mut self) -> ChainId {
        chain_id()
    }

    fn creator_chain_id(&mut self, _application_id: ApplicationId) -> ChainId {
        chain_id()
    }

    fn application_creation_account(&mut self) -> Account {
        account()
    }

    fn application_account(&mut self) -> Account {
        account()
    }

    fn application_id(&mut self) -> ApplicationId {
        application_id()
    }

    fn chain_balance(&mut self) -> Amount {
        Amount::ZERO
    }

    fn owner_balance(&mut self, _owner: AccountOwner) -> Amount {
        Amount::ZERO
    }

    fn application_parameters(&mut self) -> Self::Parameters {}

    fn block_height(&mut self) -> BlockHeight {
        BlockHeight::from(1)
    }
}

impl ContractRuntimeContext for MockRuntime {
    type Error = MockRuntimeError;
    type Message = ();

    fn authenticated_account(&mut self) -> Account {
        account()
    }

    fn authenticated_signer(&mut self) -> Option<AccountOwner> {
        Some(AccountOwner::CHAIN)
    }

    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, Self::Error> {
        Ok(AccountOwner::CHAIN)
    }

    fn authenticated_caller_id(&mut self) -> Option<ApplicationId> {
        Some(application_id())
    }

    fn require_authenticated_caller_id(&mut self) -> Result<ApplicationId, Self::Error> {
        Ok(application_id())
    }

    fn owner_accounts(&mut self) -> Vec<Account> {
        vec![account()]
    }

    fn send_message(&mut self, _destination: ChainId, _message: Self::Message, _tracking: bool) {}

    fn message_is_bouncing(&mut self) -> Option<bool> {
        None
    }

    fn message_origin_chain_id(&mut self) -> Option<ChainId> {
        Some(chain_id())
    }

    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, Self::Error> {
        Ok(chain_id())
    }

    fn message_signer_account(&mut self) -> Account {
        account()
    }

    fn message_caller_account(&mut self) -> Account {
        account()
    }

    fn create_application<Abi, Parameters, InstantiationArgument>(
        &mut self,
        _module_id: ModuleId,
        _parameters: &Parameters,
        _argument: &InstantiationArgument,
    ) -> ApplicationId<Abi>
    where
        Abi: ContractAbi,
        Parameters: Serialize,
        InstantiationArgument: Serialize,
    {
        application_id().with_abi::<Abi>()
    }

    fn call_application<A: ContractAbi + Send>(
        &mut self,
        application: ApplicationId<A>,
        call: &A::Operation,
    ) -> A::Response {
        let operation = StateAbi::deserialize_operation(
            A::serialize_operation(call).expect("serialize state operation"),
        )
        .expect("deserialize state operation");
        let response = match operation {
            StateOperation::Read { namespace, key } => {
                self.calls.push(StateCall::Read {
                    application_id: application.forget_abi(),
                    namespace,
                    key,
                });
                StateResponse::Read(
                    self.counter
                        .as_ref()
                        .map(|counter| bcs::to_bytes(counter).unwrap()),
                )
            }
            StateOperation::Write {
                namespace,
                key,
                value,
            } => {
                self.calls.push(StateCall::Write {
                    application_id: application.forget_abi(),
                    namespace,
                    key,
                    value: value.clone(),
                });
                self.counter = Some(bcs::from_bytes(&value).unwrap());
                StateResponse::Ok
            }
            other => panic!("unexpected state adapter operation: {other:?}"),
        };

        A::deserialize_response(StateAbi::serialize_response(response).unwrap())
            .expect("deserialize state response")
    }

    fn transfer(&mut self, _source: AccountOwner, _destination: Account, _amount: Amount) {}

    fn transfer_combined(
        &mut self,
        _source: Option<AccountOwner>,
        _destination: Account,
        _amount: Amount,
    ) {
    }

    fn open_chain(
        &mut self,
        _chain_ownership: ChainOwnership,
        _application_permissions: ApplicationPermissions,
        _balance: Amount,
    ) -> ChainId {
        chain_id()
    }

    fn chain_ownership(&mut self) -> ChainOwnership {
        ChainOwnership::single(AccountOwner::CHAIN)
    }

    fn change_ownership(&mut self, _ownership: ChainOwnership) -> Result<(), ChangeOwnershipError> {
        Ok(())
    }

    fn change_application_permissions(
        &mut self,
        _application_permissions: ApplicationPermissions,
    ) -> Result<(), ChangeApplicationPermissionsError> {
        Ok(())
    }

    fn application_permissions(&mut self) -> ApplicationPermissions {
        ApplicationPermissions::default()
    }
}

#[tokio::test]
async fn business_handler_uses_concrete_state_contract_adapter() {
    let state_app_id = state_application_id();
    let namespace = 7;
    let runtime = Rc::new(RefCell::new(MockRuntime::new(state_app_id, namespace)));
    let mut handler = build_example_handler_at_entry_layer(runtime.clone()).unwrap();

    let counter = handler.increment_counter().await.unwrap();

    let key = bcs::to_bytes(&ExampleBusinessKey::Counter).unwrap();
    let value = bcs::to_bytes(&ExampleCounter { value: 1 }).unwrap();
    assert_eq!(counter, ExampleCounter { value: 1 });
    assert_eq!(runtime.borrow().counter, Some(ExampleCounter { value: 1 }));
    assert_eq!(
        runtime.borrow().calls,
        vec![
            StateCall::StateAppId,
            StateCall::StateNamespace,
            StateCall::Read {
                application_id: state_app_id,
                namespace,
                key: key.clone(),
            },
            StateCall::Write {
                application_id: state_app_id,
                namespace,
                key,
                value,
            },
        ]
    );
}

fn account() -> Account {
    Account {
        chain_id: chain_id(),
        owner: AccountOwner::CHAIN,
    }
}

fn chain_id() -> ChainId {
    ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8").unwrap()
}

fn application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
}

fn state_application_id() -> ApplicationId {
    ApplicationId::new(
        CryptoHash::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap(),
    )
}
