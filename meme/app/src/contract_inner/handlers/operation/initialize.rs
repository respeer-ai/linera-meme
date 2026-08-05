use std::{cell::RefCell, rc::Rc};

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    ams::{AmsAbi, AmsOperation, Metadata, MEME},
    blob_gateway::{BlobDataType, BlobGatewayAbi, BlobGatewayOperation},
    meme::{InitializeArgument, MemeMessage, MemeOperation, MemeResponse},
    policy::open_chain_fee_budget,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};

pub struct InitializeHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    argument: InitializeArgument,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    InitializeHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeOperation) -> Self {
        let MemeOperation::Initialize { argument } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            argument: argument.clone(),
        }
    }

    fn register_logo(&mut self, argument: &InitializeArgument) {
        let Some(blob_gateway_application_id) = argument.blob_gateway_application_id else {
            return;
        };
        let Some(logo) = argument.meme.metadata.logo else {
            return;
        };

        let call = BlobGatewayOperation::Register {
            store_type: argument.meme.metadata.logo_store_type.clone(),
            data_type: BlobDataType::Image,
            blob_hash: logo,
        };

        log::info!("DEBUG MEME: registering meme logo ... {:?}", call);

        let _ = self.runtime.borrow_mut().call_application(
            blob_gateway_application_id.with_abi::<BlobGatewayAbi>(),
            &call,
        );
    }

    fn register_application(&mut self, argument: &InitializeArgument) {
        let Some(ams_application_id) = argument.ams_application_id else {
            return;
        };
        let Some(logo) = argument.meme.metadata.logo else {
            return;
        };

        let application_id = self.runtime.borrow_mut().application_id().forget_abi();
        let created_at = self.runtime.borrow_mut().system_time();
        let creator = self.runtime.borrow_mut().creator();

        let call = AmsOperation::Register {
            metadata: Metadata {
                creator,
                application_name: argument.meme.name.clone(),
                application_id,
                application_type: MEME.to_string(),
                key_words: vec![
                    "Linera".to_string(),
                    "Meme".to_string(),
                    "PoW microchain".to_string(),
                ],
                logo_store_type: argument.meme.metadata.logo_store_type.clone(),
                logo,
                description: argument.meme.metadata.description.clone(),
                twitter: argument.meme.metadata.twitter.clone(),
                telegram: argument.meme.metadata.telegram.clone(),
                discord: argument.meme.metadata.discord.clone(),
                website: argument.meme.metadata.website.clone(),
                github: argument.meme.metadata.github.clone(),
                spec: Some(
                    serde_json::to_string(&argument.meme).expect("Failed serialize meme"),
                ),
                created_at,
            },
        };

        log::info!("DEBUG MEME: registering meme ... {:?}", call);

        let _ = self
            .runtime
            .borrow_mut()
            .call_application(ams_application_id.with_abi::<AmsAbi>(), &call);
    }

    async fn create_liquidity_pool(&mut self) -> Option<HandlerOutcome<MemeMessage, MemeResponse>> {
        log::info!("DEBUG MEME: creating liquidity pool ...");

        let Ok(swap_application_id) = self.state.swap_application_id().await else {
            log::info!("DEBUG MEME: ignore creating liquidity pool for invalid swap application id");
            return None;
        };
        let Some(swap_application_id) = swap_application_id else {
            log::info!("DEBUG MEME: ignore creating liquidity pool for missing swap application id");
            return None;
        };
        let Some(liquidity) = self.runtime.borrow_mut().initial_liquidity() else {
            log::info!("DEBUG MEME: ignore creating liquidity pool for invalid initial liquidity");
            return None;
        };
        if liquidity.fungible_amount <= Amount::ZERO || liquidity.native_amount <= Amount::ZERO {
            log::info!(
                "DEBUG MEME: ignore creating liquidity pool for fungible amount {}, native amount {}",
                liquidity.fungible_amount,
                liquidity.native_amount,
            );
            return None;
        }

        let swap_creator_chain = self.runtime.borrow_mut().swap_creator_chain_id();
        self.runtime.borrow_mut().transfer_combined(
            None,
            Account {
                chain_id: swap_creator_chain,
                owner: AccountOwner::CHAIN,
            },
            open_chain_fee_budget(),
        );
        if !self.runtime.borrow_mut().virtual_initial_liquidity() {
            self.runtime.borrow_mut().transfer_combined(
                None,
                Account {
                    chain_id: swap_creator_chain,
                    owner: AccountOwner::from(swap_application_id),
                },
                liquidity.native_amount,
            );
        }

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(destination, MemeMessage::LiquidityFunded, false);

        Some(outcome)
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for InitializeHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let proxy_application_id = self
            .state
            .proxy_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        if Some(caller) != proxy_application_id {
            return Err(HandlerError::NotAllowed);
        }

        let mut argument = self.argument.clone();
        argument.owner = self.runtime.borrow_mut().creator();
        argument.holder = self.runtime.borrow_mut().application_account();
        argument.initial_owner_balance = Amount::from_tokens(100);
        argument.meme.virtual_initial_liquidity = self.runtime.borrow_mut().virtual_initial_liquidity();
        argument.meme.initial_liquidity = self.runtime.borrow_mut().initial_liquidity();
        argument.enable_mining = self.runtime.borrow_mut().enable_mining();
        argument.mining_supply = self.runtime.borrow_mut().mining_supply();
        argument.now = self.runtime.borrow_mut().system_time();
        argument.meme.total_supply = argument.meme.initial_supply;

        self.state
            .initialize(argument.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let creator = self.runtime.borrow_mut().creator();
        self.state
            .mint(creator, Amount::from_tokens(100))
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        self.register_application(&argument);
        self.register_logo(&argument);

        Ok(self.create_liquidity_pool().await)
    }
}
