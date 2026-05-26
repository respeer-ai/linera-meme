use crate::interfaces::state::StateInterface;
use abi::{
    meme::{
        MemeAbi, MemeOperation, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPurpose,
    },
    meme_token::MemeToken,
    swap::pool::{PoolMessage, PoolOperation, PoolResponse},
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

    token: Option<ApplicationId>,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ClaimHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::Claim { token, amount } = op else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,

            token: *token,
            amount: *amount,
        }
    }

    async fn claim(&mut self, token: MemeToken, owner: Account) -> Result<(), HandlerError> {
        self.state
            .claim(token, owner, self.amount)
            .await
            .map_err(Into::into)?;

        match token {
            MemeToken::Native => {
                self.transfer_native(owner);
                self.state
                    .claim_success(token, owner, self.amount)
                    .await
                    .map_err(Into::into)?;
            }
            MemeToken::Fungible(application_id) => {
                self.transfer_fungible(application_id, owner);
            }
        }

        Ok(())
    }

    fn transfer_native(&mut self, owner: Account) {
        let source = AccountOwner::from(self.runtime.borrow_mut().application_id());
        self.runtime
            .borrow_mut()
            .transfer(source, owner, self.amount);
    }

    fn transfer_fungible(&mut self, token: ApplicationId, owner: Account) {
        let call = MemeOperation::TransferFromApplicationWithReceipt {
            to: owner,
            amount: self.amount,
            receipt: TransferFromApplicationReceipt {
                purpose: TransferFromApplicationReceiptPurpose::PoolClaim,
                owner,
                token,
                amount: self.amount,
                result: None,
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

        self.state.pool().validate_token(self.token);

        let owner = self.runtime.borrow_mut().authenticated_account();
        let token = MemeToken::from(self.token);
        self.claim(token, owner).await?;

        Ok(None)
    }
}
