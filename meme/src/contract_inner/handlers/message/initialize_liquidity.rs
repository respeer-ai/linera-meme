use crate::{
    contract_inner::handlers::open_multi_leader_rounds::OpenMultiLeaderRoundsHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::{
    meme::{MemeMessage, MemeResponse},
    swap::pool::{PoolAbi, PoolInitializeLiquidityCall, PoolOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    caller: Account,
    pool_application: Account,
    amount_0: Amount,
    pool_initialize: PoolInitializeLiquidityCall,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::InitializeLiquidity {
            caller,
            pool_application,
            amount_0,
            pool_initialize,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            caller: *caller,
            pool_application: *pool_application,
            amount_0: *amount_0,
            pool_initialize: *pool_initialize,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        assert!(
            self.caller.chain_id == self.runtime.borrow_mut().swap_creator_chain_id(),
            "Invalid caller"
        );
        assert!(
            self.caller.owner
                == AccountOwner::from(self.state.borrow().swap_application_id().unwrap()),
            "Invalid caller"
        );

        let from = self.runtime.borrow_mut().application_creation_account();
        self.state
            .borrow_mut()
            .transfer_from(self.caller, from, self.pool_application, self.amount_0)
            .await
            .map_err(Into::into)?;

        let AccountOwner::Address32(application_description_hash) = self.pool_application.owner
        else {
            panic!("Invalid pool application");
        };
        let pool_application_id: ApplicationId = ApplicationId::new(application_description_hash);
        let call = PoolOperation::InitializeLiquidity {
            amount_0_in: self.amount_0,
            amount_1_in: self.pool_initialize.amount_1_in,
            to: self.pool_initialize.to,
            block_timestamp: None,
        };
        let _ = self
            .runtime
            .borrow_mut()
            .call_application(pool_application_id.with_abi::<PoolAbi>(), &call);

        // This should be the final message of initialization so we change ownership here
        let _ = OpenMultiLeaderRoundsHandler::new(self.runtime.clone(), self.state.clone())
            .handle()
            .await?;

        Ok(None)
    }
}
