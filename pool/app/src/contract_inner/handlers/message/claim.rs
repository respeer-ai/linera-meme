use crate::interfaces::state::StateInterface;
use abi::{
    meme::{
        MemeAbi, MemeOperation, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPurpose,
    },
    pool::{PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    origin: Account,
    token: Option<ApplicationId>,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ClaimHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::Claim {
            origin,
            token,
            amount,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,

            origin: *origin,
            token: *token,
            amount: *amount,
        }
    }

    async fn claim(&mut self, token: Option<ApplicationId>) -> Result<(), HandlerError> {
        self.state
            .claim(token, self.origin, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        match token {
            None => {
                self.transfer_native();
                self.state
                    .claim_success(token, self.origin, self.amount)
                    .await
                    .map_err(|error| HandlerError::ProcessError(error.into()))?;
            }
            Some(application_id) => {
                self.transfer_fungible(application_id);
            }
        }

        Ok(())
    }

    fn transfer_native(&mut self) {
        let source = AccountOwner::from(self.runtime.borrow_mut().application_id());
        self.runtime
            .borrow_mut()
            .transfer(source, self.origin, self.amount);
    }

    fn transfer_fungible(&mut self, token: ApplicationId) {
        let call = MemeOperation::TransferFromApplicationWithReceipt {
            to: self.origin,
            amount: self.amount,
            receipt: TransferFromApplicationReceipt {
                purpose: TransferFromApplicationReceiptPurpose::PoolClaim,
                owner: self.origin,
                token,
                amount: self.amount,
                result: None,
                payload: None,
            },
        };

        let _ = self
            .runtime
            .borrow_mut()
            .call_application(token.with_abi::<MemeAbi>(), &call);
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for ClaimHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(self.amount > Amount::ZERO, "Invalid amount");

        let pool = self
            .state
            .pool()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        pool.validate_token(self.token);

        self.claim(self.token).await?;

        Ok(None)
    }
}
