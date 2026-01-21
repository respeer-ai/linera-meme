use std::{cell::RefCell, rc::Rc};

use super::errors::RuntimeError;
use crate::interfaces::{
    access_control::AccessControl, base::BaseRuntimeContext, contract::ContractRuntimeContext,
    meme::MemeRuntimeContext,
};
use abi::meme::{MemeAbi, MemeOperation, MemeResponse};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, BlockHeight, ChainId,
        ChainOwnership, ChangeApplicationPermissionsError, ChangeOwnershipError, ModuleId,
        Timestamp,
    },
    Contract, ContractRuntime,
};
use serde::Serialize;

pub struct ContractRuntimeAdapter<T: Contract, M> {
    runtime: Rc<RefCell<ContractRuntime<T>>>,
    _message_marker: std::marker::PhantomData<M>,
}

impl<T: Contract, M> ContractRuntimeAdapter<T, M> {
    pub fn new(runtime: Rc<RefCell<ContractRuntime<T>>>) -> Self {
        Self {
            runtime,
            _message_marker: std::marker::PhantomData,
        }
    }
}

impl<T: Contract<Message = M>, M> BaseRuntimeContext for ContractRuntimeAdapter<T, M> {
    type Parameters = T::Parameters;

    fn chain_id(&mut self) -> ChainId {
        self.runtime.borrow_mut().chain_id()
    }

    fn system_time(&mut self) -> Timestamp {
        self.runtime.borrow_mut().system_time()
    }

    fn application_creator_chain_id(&mut self) -> ChainId {
        self.runtime.borrow_mut().application_creator_chain_id()
    }

    fn application_creation_account(&mut self) -> Account {
        let mut runtime = self.runtime.borrow_mut();

        Account {
            chain_id: runtime.application_creator_chain_id(),
            owner: AccountOwner::from(runtime.application_id().forget_abi()),
        }
    }

    fn application_account(&mut self) -> Account {
        let mut runtime = self.runtime.borrow_mut();

        Account {
            chain_id: runtime.chain_id(),
            owner: AccountOwner::from(runtime.application_id().forget_abi()),
        }
    }

    fn application_id(&mut self) -> ApplicationId {
        self.runtime.borrow_mut().application_id().forget_abi()
    }

    fn chain_balance(&mut self) -> Amount {
        self.runtime.borrow_mut().chain_balance()
    }

    fn owner_balance(&mut self, owner: AccountOwner) -> Amount {
        self.runtime.borrow_mut().owner_balance(owner)
    }

    fn application_parameters(&mut self) -> T::Parameters {
        self.runtime.borrow_mut().application_parameters()
    }

    fn block_height(&mut self) -> BlockHeight {
        self.runtime.borrow_mut().block_height()
    }
}

impl<T: Contract<Message = M>, M: Serialize> ContractRuntimeContext
    for ContractRuntimeAdapter<T, M>
{
    type Error = RuntimeError;
    type Message = M;

    fn authenticated_account(&mut self) -> Account {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let owner = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .unwrap_or(AccountOwner::CHAIN);

        Account { chain_id, owner }
    }

    fn authenticated_signer(&mut self) -> Option<AccountOwner> {
        self.runtime.borrow_mut().authenticated_signer()
    }

    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, RuntimeError> {
        self.runtime
            .borrow_mut()
            .authenticated_signer()
            .ok_or(RuntimeError::InvalidAuthenticatedSigner)
    }

    fn authenticated_caller_id(&mut self) -> Option<ApplicationId> {
        self.runtime.borrow_mut().authenticated_caller_id()
    }

    fn require_authenticated_caller_id(&mut self) -> Result<ApplicationId, RuntimeError> {
        self.runtime
            .borrow_mut()
            .authenticated_caller_id()
            .ok_or(RuntimeError::InvalidAuthenticatedCaller)
    }

    fn owner_accounts(&mut self) -> Vec<Account> {
        let chain_id = self.runtime.borrow_mut().chain_id();
        self.runtime
            .borrow_mut()
            .chain_ownership()
            .all_owners()
            .map(|&owner| Account { chain_id, owner })
            .collect()
    }

    fn send_message(&mut self, destination: ChainId, message: M) {
        self.runtime
            .borrow_mut()
            .prepare_message(message)
            .with_authentication()
            .send_to(destination);
    }

    fn message_origin_chain_id(&mut self) -> Option<ChainId> {
        self.runtime.borrow_mut().message_origin_chain_id()
    }

    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, RuntimeError> {
        self.runtime
            .borrow_mut()
            .message_origin_chain_id()
            .ok_or(RuntimeError::InvalidMessageOriginChainId)
    }

    fn message_signer_account(&mut self) -> Account {
        let mut runtime = self.runtime.borrow_mut();

        Account {
            chain_id: runtime
                .message_origin_chain_id()
                .expect("Invalid message origin chain"),
            owner: runtime
                .authenticated_signer()
                .expect("Invalid authenticated signer"),
        }
    }

    fn message_caller_account(&mut self) -> Account {
        let mut runtime = self.runtime.borrow_mut();

        Account {
            chain_id: runtime
                .message_origin_chain_id()
                .expect("Invalid message origin chain"),
            owner: AccountOwner::from(
                runtime
                    .authenticated_caller_id()
                    .expect("Invalid authenticated caller"),
            ),
        }
    }

    fn create_application<Abi, Parameters, InstantiationArgument>(
        &mut self,
        module_id: ModuleId,
        parameters: &Parameters,
        argument: &InstantiationArgument,
    ) -> ApplicationId<Abi>
    where
        Abi: ContractAbi,
        Parameters: Serialize,
        InstantiationArgument: Serialize,
    {
        self.runtime
            .borrow_mut()
            .create_application(module_id, parameters, argument, vec![])
    }

    fn call_application<A: ContractAbi + Send>(
        &mut self,
        application: ApplicationId<A>,
        call: &A::Operation,
    ) -> A::Response {
        self.runtime
            .borrow_mut()
            .call_application(true, application, call)
    }

    fn transfer(&mut self, source: AccountOwner, destination: Account, amount: Amount) {
        self.runtime
            .borrow_mut()
            .transfer(source, destination, amount)
    }

    fn transfer_combined(
        &mut self,
        source: Option<AccountOwner>,
        destination: Account,
        amount: Amount,
    ) {
        let owner = source.unwrap_or(self.runtime.borrow_mut().authenticated_signer().unwrap());

        let owner_balance = self.runtime.borrow_mut().owner_balance(owner);
        let chain_balance = self.runtime.borrow_mut().chain_balance();

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount <= owner_balance {
            Amount::ZERO
        } else {
            amount.try_sub(owner_balance).expect("Invalid amount")
        };

        assert!(from_owner_balance <= owner_balance, "Insufficient balance");
        assert!(from_chain_balance <= chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime
                .borrow_mut()
                .transfer(owner, destination, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.borrow_mut().transfer(
                AccountOwner::CHAIN,
                destination,
                from_chain_balance,
            );
        }
    }

    fn open_chain(
        &mut self,
        chain_ownership: ChainOwnership,
        application_permissions: ApplicationPermissions,
        balance: Amount,
    ) -> ChainId {
        self.runtime
            .borrow_mut()
            .open_chain(chain_ownership, application_permissions, balance)
    }

    fn chain_ownership(&mut self) -> ChainOwnership {
        self.runtime.borrow_mut().chain_ownership()
    }

    fn change_ownership(&mut self, ownership: ChainOwnership) -> Result<(), ChangeOwnershipError> {
        self.runtime.borrow_mut().change_ownership(ownership)
    }

    fn change_application_permissions(
        &mut self,
        application_permissions: ApplicationPermissions,
    ) -> Result<(), ChangeApplicationPermissionsError> {
        self.runtime
            .borrow_mut()
            .change_application_permissions(application_permissions)
    }

    fn application_permissions(&mut self) -> ApplicationPermissions {
        // Validators don't support get application permissions right now so disable it
        // self.runtime.borrow_mut().application_permissions()
        ApplicationPermissions::default()
    }
}

impl<T: Contract<Message = M>, M> AccessControl for ContractRuntimeAdapter<T, M> {
    type Error = RuntimeError;

    fn only_application_creator(&mut self) -> Result<(), RuntimeError> {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let creator_chain_id = self.runtime.borrow_mut().application_creator_chain_id();

        (chain_id == creator_chain_id)
            .then_some(())
            .ok_or(RuntimeError::PermissionDenied(
                "Only allow application creator".to_string(),
            ))
    }
}

impl<T: Contract<Message = M>, M> MemeRuntimeContext for ContractRuntimeAdapter<T, M> {
    type Error = RuntimeError;

    fn token_creator_chain_id(&mut self, token: ApplicationId) -> Result<ChainId, RuntimeError> {
        let call = MemeOperation::CreatorChainId;
        let MemeResponse::ChainId(chain_id) =
            self.runtime
                .borrow_mut()
                .call_application(true, token.with_abi::<MemeAbi>(), &call)
        else {
            return Err(RuntimeError::InvalidApplicationResponse);
        };

        Ok(chain_id)
    }
}
