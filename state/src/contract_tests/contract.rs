use super::super::StateContract as StateAppContract;
use abi::state::{StateAbi, StateBaseInterface, StateMessage, StateOperation, StateResponse};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationDescription, ApplicationId,
        ApplicationPermissions, BlockHeight, ChainId, ChainOwnership,
        ChangeApplicationPermissionsError, ChangeOwnershipError, CryptoHash, ModuleId, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use runtime::interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext};
use serde::{Deserialize, Serialize};
use state::{
    adapters::contract::StateContract, interfaces::contract::StateContractInterface, state::State,
};
use std::{
    cell::RefCell,
    error::Error,
    fmt,
    panic::{catch_unwind, AssertUnwindSafe},
    rc::Rc,
    str::FromStr,
};

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
        operator_account()
    }

    fn application_account(&mut self) -> Account {
        operator_account()
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
        operator_account()
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
        vec![operator_account()]
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
        operator_account()
    }

    fn message_caller_account(&mut self) -> Account {
        operator_account()
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
    let state_adapter = StateContract::new(runtime.clone()).unwrap();
    let mut handler = ExampleBusinessHandler::new(state_adapter);

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

#[tokio::test]
async fn initialize_operator_rejects_repeated_initialization() {
    let mut contract = create_and_instantiate_state_contract();

    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );
    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: other_operator_account(),
            })
            .blocking_wait();
    }));

    assert!(result.is_err());
    assert_eq!(
        *contract.state.borrow().operator.get(),
        Some(operator_account())
    );
}

#[tokio::test]
async fn batch_write_read_delete_isolated_by_authenticated_application_slot() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );

    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );
    set_authenticated_caller(&mut contract, other_application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );

    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchWrite {
                namespace: 1,
                writes: vec![(b"shared".to_vec(), b"first".to_vec())],
            })
            .await,
        StateResponse::Ok
    );

    set_authenticated_caller(&mut contract, other_application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchWrite {
                namespace: 1,
                writes: vec![(b"shared".to_vec(), b"second".to_vec())],
            })
            .await,
        StateResponse::Ok
    );
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchRead {
                namespace: 1,
                keys: vec![b"shared".to_vec()],
            })
            .await,
        StateResponse::BatchRead(vec![Some(b"second".to_vec())])
    );

    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchRead {
                namespace: 1,
                keys: vec![b"shared".to_vec()],
            })
            .await,
        StateResponse::BatchRead(vec![Some(b"first".to_vec())])
    );
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchDelete {
                namespace: 1,
                keys: vec![b"shared".to_vec()],
            })
            .await,
        StateResponse::Ok
    );
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchRead {
                namespace: 1,
                keys: vec![b"shared".to_vec()],
            })
            .await,
        StateResponse::BatchRead(vec![None])
    );

    set_authenticated_caller(&mut contract, other_application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::BatchRead {
                namespace: 1,
                keys: vec![b"shared".to_vec()],
            })
            .await,
        StateResponse::BatchRead(vec![Some(b"second".to_vec())])
    );
}

#[tokio::test]
async fn frozen_namespace_rejects_management_and_allows_record_access() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );
    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );

    set_message_signer(&mut contract, operator_account());
    contract
        .execute_message(StateMessage::FreezeNamespace)
        .await;

    set_authenticated_caller(&mut contract, other_application_id());
    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .blocking_wait();
    }));
    assert!(result.is_err());

    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::Write {
                namespace: 1,
                key: b"key".to_vec(),
                value: b"value".to_vec(),
            })
            .await,
        StateResponse::Ok
    );
    assert_eq!(
        contract
            .execute_operation(StateOperation::Read {
                namespace: 1,
                key: b"key".to_vec(),
            })
            .await,
        StateResponse::Read(Some(b"value".to_vec()))
    );
}

#[tokio::test]
async fn set_operator_message_rejects_non_current_operator_and_rotates_authorization() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );

    let result = catch_unwind(AssertUnwindSafe(|| {
        set_message_signer(&mut contract, other_operator_account());
        contract
            .execute_message(StateMessage::SetOperator {
                new_operator: other_operator_account(),
            })
            .blocking_wait();
    }));
    assert!(result.is_err());
    assert_eq!(
        *contract.state.borrow().operator.get(),
        Some(operator_account())
    );

    set_message_signer(&mut contract, operator_account());
    contract
        .execute_message(StateMessage::SetOperator {
            new_operator: other_operator_account(),
        })
        .await;
    assert_eq!(
        *contract.state.borrow().operator.get(),
        Some(other_operator_account())
    );

    set_message_signer(&mut contract, other_operator_account());
    contract
        .execute_message(StateMessage::FreezeNamespace)
        .await;
    assert_eq!(*contract.state.borrow().frozen_namespaces.get(), true);
}

#[tokio::test]
async fn handoff_preserves_slot_records_and_rejects_old_application() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );
    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );
    assert_eq!(
        contract
            .execute_operation(StateOperation::Write {
                namespace: 1,
                key: b"migrated".to_vec(),
                value: b"kept".to_vec(),
            })
            .await,
        StateResponse::Ok
    );

    set_message_signer(&mut contract, operator_account());
    contract
        .execute_message(StateMessage::Handoff {
            application_id: application_id(),
            namespace: 1,
            new_application_id: other_application_id(),
        })
        .await;

    set_authenticated_caller(&mut contract, other_application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::Read {
                namespace: 1,
                key: b"migrated".to_vec(),
            })
            .await,
        StateResponse::Read(Some(b"kept".to_vec()))
    );

    set_authenticated_caller(&mut contract, application_id());
    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::Read {
                namespace: 1,
                key: b"migrated".to_vec(),
            })
            .blocking_wait();
    }));
    assert!(result.is_err());
}

#[tokio::test]
async fn management_operations_reject_missing_signer() {
    let mut contract = create_and_instantiate_state_contract();
    contract.runtime.borrow_mut().set_authenticated_signer(None);

    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::SetOperator {
                application_id: application_id(),
                new_operator: other_operator_account(),
            })
            .blocking_wait();
    }));

    assert!(result.is_err());
    assert_eq!(*contract.state.borrow().operator.get(), None);
}

#[tokio::test]
async fn create_namespace_rejects_wrong_creator_chain_and_unbound_caller_reads() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );
    contract
        .runtime
        .borrow_mut()
        .set_application_description(application_id(), application_description(other_chain_id()));

    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .blocking_wait();
    }));
    assert!(result.is_err());

    contract
        .runtime
        .borrow_mut()
        .set_application_description(application_id(), application_description(chain_id()));
    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );

    set_authenticated_caller(&mut contract, other_application_id());
    let result = catch_unwind(AssertUnwindSafe(|| {
        contract
            .execute_operation(StateOperation::BatchRead {
                namespace: 1,
                keys: vec![b"missing".to_vec()],
            })
            .blocking_wait();
    }));

    assert!(result.is_err());
}

#[tokio::test]
async fn handoff_rejects_already_bound_target_without_replacing_source() {
    let mut contract = create_and_instantiate_state_contract();
    assert_eq!(
        contract
            .execute_operation(StateOperation::InitializeOperator {
                operator: operator_account(),
            })
            .await,
        StateResponse::Ok
    );
    set_authenticated_caller(&mut contract, application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );
    set_authenticated_caller(&mut contract, other_application_id());
    assert_eq!(
        contract
            .execute_operation(StateOperation::CreateNamespace { namespace: 1 })
            .await,
        StateResponse::Ok
    );

    let result = catch_unwind(AssertUnwindSafe(|| {
        set_message_signer(&mut contract, operator_account());
        contract
            .execute_message(StateMessage::Handoff {
                application_id: application_id(),
                namespace: 1,
                new_application_id: other_application_id(),
            })
            .blocking_wait();
    }));

    assert!(result.is_err());
    assert_eq!(
        contract
            .state
            .borrow()
            .namespace_apps
            .get(&1)
            .await
            .unwrap()
            .unwrap(),
        vec![application_id(), other_application_id()]
    );
}

#[tokio::test]
async fn set_operator_operation_routes_message_without_reading_state() {
    let mut contract = create_and_instantiate_state_contract();
    let response = contract
        .execute_operation(StateOperation::SetOperator {
            application_id: application_id(),
            new_operator: other_operator_account(),
        })
        .await;

    assert_eq!(response, StateResponse::Ok);
    assert_eq!(*contract.state.borrow().operator.get(), None);
    let runtime = contract.runtime.borrow();
    let messages = runtime.created_send_message_requests();
    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].destination, chain_id());
    assert_eq!(
        messages[0].message,
        StateMessage::SetOperator {
            new_operator: other_operator_account()
        }
    );
    assert_eq!(messages[0].is_tracked, false);
}

fn create_and_instantiate_state_contract() -> StateAppContract {
    let runtime = ContractRuntime::new()
        .with_application_parameters(())
        .with_authenticated_signer(operator_account().owner)
        .with_authenticated_caller_id(application_id())
        .with_chain_id(chain_id())
        .with_application_creator_chain_id(chain_id())
        .with_application_description(application_id(), application_description(chain_id()))
        .with_application_description(other_application_id(), application_description(chain_id()))
        .with_chain_ownership(ChainOwnership::single(operator_account().owner))
        .with_system_time(Timestamp::from(1))
        .with_block_height(BlockHeight::from(1))
        .with_application_id(state_application_id().with_abi::<StateAbi>());

    let mut contract = StateAppContract {
        state: Rc::new(RefCell::new(
            State::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    contract.instantiate(()).blocking_wait();
    contract
}

fn set_authenticated_caller(contract: &mut StateAppContract, caller: ApplicationId) {
    contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(caller);
}

fn set_message_signer(contract: &mut StateAppContract, signer: Account) {
    contract
        .runtime
        .borrow_mut()
        .set_authenticated_signer(Some(signer.owner));
    contract
        .runtime
        .borrow_mut()
        .set_message_origin_chain_id(Some(signer.chain_id));
}

fn application_description(creator_chain_id: ChainId) -> ApplicationDescription {
    ApplicationDescription {
        module_id: ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap(),
        creator_chain_id,
        block_height: BlockHeight::from(1),
        application_index: 0,
        parameters: Vec::new(),
        required_application_ids: Vec::new(),
    }
}

fn operator_account() -> Account {
    Account {
        chain_id: chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap(),
    }
}

fn other_operator_account() -> Account {
    Account {
        chain_id: other_chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
        )
        .unwrap(),
    }
}

fn chain_id() -> ChainId {
    ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8").unwrap()
}

fn other_chain_id() -> ChainId {
    ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65").unwrap()
}

fn application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
}

fn other_application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
        .unwrap()
}

fn state_application_id() -> ApplicationId {
    ApplicationId::new(
        CryptoHash::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap(),
    )
}
