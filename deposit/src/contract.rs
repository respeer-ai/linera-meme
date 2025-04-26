#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};

use self::state::DepositState;
use abi::deposit::{DepositAbi, DepositOperation, DepositResponse};
use deposit::DepositError;

pub struct ApplicationContract {
    state: DepositState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(ApplicationContract);

impl WithContractAbi for ApplicationContract {
    type Abi = DepositAbi;
}

impl Contract for ApplicationContract {
    type Message = ();
    type Parameters = ();
    type InstantiationArgument = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = DepositState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ApplicationContract { state, runtime }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {}

    async fn execute_operation(&mut self, operation: DepositOperation) -> DepositResponse {
        match operation {
            DepositOperation::Deposit { to, amount } => self
                .on_op_deposit(to, amount)
                .await
                .expect("Failed OP: deposit"),
        }
    }

    async fn execute_message(&mut self, _message: Self::Message) {
        panic!("Deposit must only be happen on user chain");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl ApplicationContract {
    async fn on_op_deposit(
        &mut self,
        to: Account,
        amount: Amount,
    ) -> Result<DepositResponse, DepositError> {
        let timestamp = self.runtime.system_time();

        let owner = self.runtime.authenticated_signer().unwrap();

        let owner_balance = self.runtime.owner_balance(owner);
        let chain_balance = self.runtime.chain_balance();

        // TODO: create message with grant here
        // TODO: if there is no balance on target chain, it won't be received
        // TODO: how to set grant with transfer here ?

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount > owner_balance {
            amount.saturating_sub(owner_balance)
        } else {
            Amount::ZERO
        };

        assert!(from_owner_balance < owner_balance, "Insufficient balance");
        assert!(from_chain_balance < chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime.transfer(owner, to, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime
                .transfer(AccountOwner::CHAIN, to, from_chain_balance);
        }

        self.state.deposit(to, amount, timestamp);

        Ok(DepositResponse::Ok)
    }
}
