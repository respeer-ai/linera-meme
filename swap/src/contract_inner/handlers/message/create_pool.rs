use crate::interfaces::state::StateInterface;
use abi::pool::{
    state_v1::{PoolStateAbi, StateInstantiationArgument},
    BootstrapPolicy, InstantiationArgument as PoolInstantiationArgument, PoolAbi,
    PoolInitializeArgument, PoolOperation, PoolParameters,
};
use abi::swap::router::{SwapMessage, SwapResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ModuleId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct CreatePoolHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    creator: Account,
    pool_bytecode_id: ModuleId,
    pool_state_bytecode_ids: Vec<(u16, ModuleId)>,
    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    bootstrap_policy: BootstrapPolicy,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    CreatePoolHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::CreatePool {
            creator,
            pool_bytecode_id,
            pool_state_bytecode_ids,
            token_0,
            token_1,
            amount_0,
            amount_1,
            bootstrap_policy,
            to,
            ..
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            creator: *creator,
            pool_bytecode_id: *pool_bytecode_id,
            pool_state_bytecode_ids: pool_state_bytecode_ids.clone(),
            token_0: *token_0,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            bootstrap_policy: bootstrap_policy.clone(),
            to: *to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage, SwapResponse> for CreatePoolHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<SwapMessage, SwapResponse>>, HandlerError> {
        // Run on pool chain
        let application_id = self.runtime.borrow_mut().application_id();
        let chain_id = self.runtime.borrow_mut().chain_id();

        let (amount_0_in, amount_1_in) = match &self.bootstrap_policy {
            BootstrapPolicy::MemeInitializeLiquidity {
                virtual_initial_liquidity: _,
            } => (self.amount_0, self.amount_1),
            BootstrapPolicy::UserCreatePool => (Amount::ZERO, Amount::ZERO),
        };

        let pool_application_id = self
            .runtime
            .borrow_mut()
            .create_application::<PoolAbi, PoolParameters, PoolInstantiationArgument>(
                self.pool_bytecode_id,
                &PoolParameters {
                    creator: self.creator,
                    token_0: self.token_0,
                    token_1: self.token_1,
                    bootstrap_policy: self.bootstrap_policy.clone(),
                },
                &PoolInstantiationArgument {
                    pool_fee_percent_mul_100: 30,
                    router_application_id: application_id,
                    amount_0_in,
                    amount_1_in,
                },
            )
            .forget_abi();

        // Deploy the pool state apps alongside the business app so the pool
        // is fully initialized in the same flow, mirroring how the proxy
        // creates meme business and state apps together. The bytecode ids
        // travel in the message because this handler runs on the pool chain
        // where swap state was never instantiated.
        let pool_state_bytecode_ids = self.pool_state_bytecode_ids.clone();
        let swap_application_id = application_id.forget_abi();
        let operator = Account {
            chain_id: self.runtime.borrow_mut().application_creator_chain_id(),
            owner: AccountOwner::from(swap_application_id),
        };
        let state_application_ids: Vec<ApplicationId> = pool_state_bytecode_ids
            .into_iter()
            .map(|(_, bytecode_id)| {
                self.runtime
                    .borrow_mut()
                    .create_application::<PoolStateAbi, (), StateInstantiationArgument>(
                        bytecode_id,
                        &(),
                        &StateInstantiationArgument {
                            business_application_id: pool_application_id,
                            operator: Some(operator),
                        },
                    )
                    .forget_abi()
            })
            .collect();

        let _ = self.runtime.borrow_mut().call_application(
            pool_application_id.with_abi::<PoolAbi>(),
            &PoolOperation::AppendStates {
                state_application_ids: state_application_ids.clone(),
            },
        );
        let _ = self.runtime.borrow_mut().call_application(
            pool_application_id.with_abi::<PoolAbi>(),
            &PoolOperation::Initialize {
                argument: PoolInitializeArgument {
                    router_application_id: swap_application_id,
                    pool_fee_percent_mul_100: 30,
                },
            },
        );

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let pool_application = Account {
            chain_id,
            owner: AccountOwner::from(pool_application_id),
        };
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::PoolCreated {
                creator: self.creator,
                pool_application,
                token_0: self.token_0,
                token_1: self.token_1,
                amount_0: self.amount_0,
                amount_1: self.amount_1,
                bootstrap_policy: self.bootstrap_policy.clone(),
                to: self.to,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
