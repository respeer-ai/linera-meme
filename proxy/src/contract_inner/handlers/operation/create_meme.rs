use crate::interfaces::state::StateInterface;
use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    policy::open_chain_fee_budget,
    proxy::{ProxyMessage, ProxyOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct CreateMemeHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    meme_instantiation_argument: MemeInstantiationArgument,
    meme_parameters: MemeParameters,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    CreateMemeHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::CreateMeme {
            meme_instantiation_argument,
            meme_parameters,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            meme_instantiation_argument: meme_instantiation_argument.clone(),
            meme_parameters: meme_parameters.clone(),
        }
    }

    fn fund_proxy_chain(&mut self, to: AccountOwner, amount: Amount) {
        let to = Account {
            chain_id: self.runtime.borrow_mut().application_creator_chain_id(),
            owner: to,
        };

        self.runtime
            .borrow_mut()
            .transfer_combined(None, to, amount);
    }

    fn fund_proxy_chain_initial_liquidity(&mut self, meme_parameters: MemeParameters) {
        if meme_parameters.virtual_initial_liquidity {
            return;
        }
        let Some(liquidity) = meme_parameters.initial_liquidity else {
            return;
        };
        // We cannot fund to application directly. Due to we're not owner of the chain then we
        // cannot transfer the fund to swap. We should fund ourself on the target chain
        // let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        self.fund_proxy_chain(signer, liquidity.native_amount);
    }

    fn fund_proxy_chain_fee_budget(&mut self, fund_pool_fee: bool) {
        // Open chain budget fee for meme chain
        self.fund_proxy_chain(AccountOwner::CHAIN, open_chain_fee_budget());
        if !fund_pool_fee {
            return;
        }
        // Open chain budget fee for pool chain
        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        self.fund_proxy_chain(signer, open_chain_fee_budget());
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage> for CreateMemeHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<ProxyMessage>>, HandlerError> {
        log::info!("DEBUG PROXY:OP creating meme ...");

        self.meme_instantiation_argument.proxy_application_id =
            Some(self.runtime.borrow_mut().application_id().forget_abi());
        self.meme_instantiation_argument
            .meme
            .virtual_initial_liquidity = self.meme_parameters.virtual_initial_liquidity;
        self.meme_instantiation_argument.meme.initial_liquidity =
            self.meme_parameters.initial_liquidity.clone();

        // Fund proxy application on the creation chain, it'll fund meme chain for fee and
        // initial liquidity
        self.fund_proxy_chain_fee_budget(self.meme_parameters.initial_liquidity.is_some());
        self.fund_proxy_chain_initial_liquidity(self.meme_parameters.clone());

        self.meme_parameters.creator = self.runtime.borrow_mut().authenticated_account();

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            ProxyMessage::CreateMeme {
                instantiation_argument: self.meme_instantiation_argument.clone(),
                parameters: self.meme_parameters.clone(),
            },
        );

        Ok(Some(outcome))
    }
}
