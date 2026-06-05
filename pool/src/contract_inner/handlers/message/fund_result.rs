use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme::{
        MemeAbi, MemeOperation, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPayload, TransferFromApplicationReceiptPurpose,
    },
    meme_token::MemeToken,
    swap::pool::{
        AddLiquidityTransferReceiptPayload, FundRequest, FundType, PoolMessage, PoolResponse,
        SwapTransferReceiptPayload,
    },
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct FundResultHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,
    prev: Option<FundRequest>,
    request: FundRequest,
    next: Option<FundRequest>,
    result: Result<(), String>,
}

impl<R, S> FundResultHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::FundResult {
            prev,
            request,
            next,
            result,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state: Rc::new(RefCell::new(state)),
            prev: prev.clone(),
            request: request.clone(),
            next: next.clone(),
            result: result.clone(),
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
            self.runtime.borrow_mut().message_origin_chain_id(),
            Some(expected_token_chain),
            "Invalid fund result origin"
        );
        let chain_id = self.runtime.borrow_mut().chain_id();
        assert_eq!(
            chain_id, self.request.from.chain_id,
            "Invalid fund result chain"
        );

        assert_eq!(
            self.runtime.borrow_mut().message_signer_account().owner,
            self.request.from.owner,
            "Invalid fund result signer"
        );
    }

    async fn credit_request(&mut self, request: &FundRequest) -> Result<(), HandlerError> {
        self.state
            .borrow_mut()
            .credit(
                MemeToken::from(request.token),
                request.from,
                request.amount_in,
            )
            .await
            .map_err(Into::into)
    }

    async fn settle_failed_transfer(&mut self) -> Result<(), HandlerError> {
        if let Some(prev) = self.prev.clone() {
            self.credit_request(&prev).await?;
        }

        Ok(())
    }

    fn fund_pool_chain_for_add_liquidity(&mut self) {
        let token = self.request.token.expect("Invalid fund token");
        let chain_id = self.runtime.borrow_mut().application_creator_chain_id();
        let application_id = self.runtime.borrow_mut().application_id();
        let to = Account {
            chain_id,
            owner: AccountOwner::from(application_id),
        };

        let call = MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: self.request.amount_in,
            receipt: TransferFromApplicationReceipt {
                purpose: TransferFromApplicationReceiptPurpose::PoolAddLiquidity,
                owner: self.request.from,
                token,
                amount: self.request.amount_in,
                result: None,
                payload: Some(TransferFromApplicationReceiptPayload::PoolAddLiquidity(
                    AddLiquidityTransferReceiptPayload {
                        prev: self.prev.clone(),
                        request: self.request.clone(),
                        next: self.next.clone(),
                    },
                )),
            },
        };

        let _ = self
            .runtime
            .borrow_mut()
            .call_application(token.with_abi::<MemeAbi>(), &call);
    }

    fn fund_pool_chain_for_swap(&mut self) {
        let token = self.request.token.expect("Invalid fund token");
        let chain_id = self.runtime.borrow_mut().application_creator_chain_id();
        let application_id = self.runtime.borrow_mut().application_id();
        let to = Account {
            chain_id,
            owner: AccountOwner::from(application_id),
        };

        let call = MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: self.request.amount_in,
            receipt: TransferFromApplicationReceipt {
                purpose: TransferFromApplicationReceiptPurpose::PoolSwap,
                owner: self.request.from,
                token,
                amount: self.request.amount_in,
                result: None,
                payload: Some(TransferFromApplicationReceiptPayload::PoolSwap(
                    SwapTransferReceiptPayload {
                        request: self.request.clone(),
                    },
                )),
            },
        };

        let _ = self
            .runtime
            .borrow_mut()
            .call_application(token.with_abi::<MemeAbi>(), &call);
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<PoolMessage, PoolResponse> for FundResultHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        self.validate();

        if self.result.is_err() {
            if self.request.fund_type == FundType::AddLiquidity {
                self.settle_failed_transfer().await?;
            }
            return Ok(None);
        }

        match self.request.fund_type {
            FundType::AddLiquidity => self.fund_pool_chain_for_add_liquidity(),
            FundType::Swap => self.fund_pool_chain_for_swap(),
            FundType::InitializeLiquidity => {
                panic!("FundRequest is not enabled for InitializeLiquidity")
            }
        }

        Ok(None)
    }
}
