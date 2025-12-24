use crate::interfaces::state::StateInterface;
use abi::{
    policy::open_chain_fee_budget,
    swap::router::{SwapMessage, SwapOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreatePoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreatePoolHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &SwapOperation) -> Self {
        let SwapOperation::CreatePool {
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
            ..
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            token_0: *token_0,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            to: *to,
        }
    }
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreatePoolHandler<R, S> {
    fn fund_swap_creator_chain(
        &mut self,
        from_owner: AccountOwner,
        to_owner: AccountOwner,
        amount: Amount,
    ) {
        let chain_id = self.runtime.borrow_mut().application_creator_chain_id();

        let owner_balance = self.runtime.borrow_mut().owner_balance(from_owner);
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
            self.runtime.borrow_mut().transfer(
                from_owner,
                Account {
                    chain_id,
                    owner: to_owner,
                },
                from_owner_balance,
            );
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.borrow_mut().transfer(
                AccountOwner::CHAIN,
                Account {
                    chain_id,
                    owner: to_owner,
                },
                from_chain_balance,
            );
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<SwapMessage>
    for CreatePoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        let signer = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .expect("Invalid signer");
        self.fund_swap_creator_chain(signer, AccountOwner::CHAIN, open_chain_fee_budget());

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::CreateUserPool {
                token_0: self.token_0,
                token_1: self.token_1,
                amount_0: self.amount_0,
                amount_1: self.amount_1,
                to: self.to,
            },
        );

        Ok(Some(outcome))
    }
}
