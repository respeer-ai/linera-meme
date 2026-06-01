use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme::{MemeAbi, MemeOperation, MemeResponse},
    swap::pool::{FundRequestExt, PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RequestFundExtHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,
    prev: Option<FundRequestExt>,
    request: FundRequestExt,
    next: Option<FundRequestExt>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > RequestFundExtHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::RequestFundExt {
            prev,
            request,
            next,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            _state: state,
            prev: prev.clone(),
            request: request.clone(),
            next: next.clone(),
        }
    }

    fn validate(&mut self) {
        assert!(self.request.amount_in > Amount::ZERO, "Invalid amount");

        let token = self.request.token.expect("Invalid fund token");
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();
        assert!(
            token == token_0 || Some(token) == token_1,
            "Invalid fund token"
        );

        let expected_token_chain = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(token)
            .expect("Failed: token creator chain id");
        assert_eq!(
            self.runtime.borrow_mut().chain_id(),
            expected_token_chain,
            "Invalid fund request chain"
        );
        let message_origin_chain_id = self.runtime.borrow_mut().message_origin_chain_id();
        assert_eq!(
            message_origin_chain_id,
            Some(self.request.from.chain_id),
            "Invalid fund request origin"
        );
        assert_eq!(
            self.runtime.borrow_mut().message_signer_account().owner,
            self.request.from.owner,
            "Invalid fund signer"
        );
    }

    fn transfer_to_caller(&mut self) -> Result<(), String> {
        let token = self.request.token.expect("Invalid fund token");
        let call = MemeOperation::TransferToCaller {
            amount: self.request.amount_in,
        };

        match self
            .runtime
            .borrow_mut()
            .call_application(token.with_abi::<MemeAbi>(), &call)
        {
            MemeResponse::Ok => Ok(()),
            MemeResponse::Fail(error) => Err(error),
            _ => panic!("Invalid response"),
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for RequestFundExtHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        self.validate();

        let destination = self
            .runtime
            .borrow_mut()
            .require_message_origin_chain_id()
            .expect("Failed: require message origin chain id");
        let result = self.transfer_to_caller();

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            PoolMessage::FundResultExt {
                prev: self.prev.clone(),
                request: self.request.clone(),
                next: self.next.clone(),
                result,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
