use std::{cell::RefCell, rc::Rc};

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    ams::{AmsAbi, AmsOperation, Metadata, MEME},
    blob_gateway::{BlobDataType, BlobGatewayAbi, BlobGatewayOperation},
    meme::{InstantiationArgument, MemeMessage, MemeResponse},
    policy::open_chain_fee_budget,
};
use base::handler::{HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, base::BaseRuntimeContext, contract::ContractRuntimeContext,
    meme::MemeRuntimeContext,
};

pub struct InstantiationHandler<
    R: ContractRuntimeContext
        + BaseRuntimeContext
        + AccessControl
        + MemeRuntimeContext
        + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    argument: InstantiationArgument,
}

impl<
        R: ContractRuntimeContext
            + BaseRuntimeContext
            + AccessControl
            + MemeRuntimeContext
            + ParametersInterface,
        S: StateInterface,
    > InstantiationHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, argument: InstantiationArgument) -> Self {
        Self {
            state,
            runtime,
            argument,
        }
    }

    fn register_logo(&mut self) {
        if let Some(blob_gateway_application_id) = self.state.blob_gateway_application_id() {
            let call = BlobGatewayOperation::Register {
                store_type: self.state.logo_store_type(),
                data_type: BlobDataType::Image,
                blob_hash: self.state.logo(),
            };

            log::info!("DEBUG MEME: registering meme logo ... {:?}", call);

            let _ = self.runtime.borrow_mut().call_application(
                blob_gateway_application_id.with_abi::<BlobGatewayAbi>(),
                &call,
            );
        }
    }

    fn register_application(&mut self) {
        let application_id = self.runtime.borrow_mut().application_id().forget_abi();
        let created_at = self.runtime.borrow_mut().system_time();
        let creator = self.runtime.borrow_mut().creator();

        if let Some(ams_application_id) = self.state.ams_application_id() {
            let call = AmsOperation::Register {
                metadata: Metadata {
                    creator,
                    application_name: self.state.name(),
                    application_id,
                    application_type: MEME.to_string(),
                    key_words: vec![
                        "Linera".to_string(),
                        "Meme".to_string(),
                        "PoW microchain".to_string(),
                    ],
                    logo_store_type: self.state.logo_store_type(),
                    logo: self.state.logo(),
                    description: self.state.description(),
                    twitter: self.state.twitter(),
                    telegram: self.state.telegram(),
                    discord: self.state.discord(),
                    website: self.state.website(),
                    github: self.state.github(),
                    spec: Some(
                        serde_json::to_string(&self.state.meme()).expect("Failed serialize meme"),
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
    }

    fn create_liquidity_pool(&mut self) -> Option<HandlerOutcome<MemeMessage, MemeResponse>> {
        log::info!("DEBUG MEME: creating liquidity pool ...");

        let Some(swap_application_id) = self.state.swap_application_id() else {
            log::info!(
                "DEBUG MEME: ignore creating liquidity pool for invalid swap application id"
            );
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

        // Meme chain will be created by swap creator chain, so we fund signer on swap creator
        // chain then it'll fund meme chain
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
            // At this moment (instantiating) there is no balance on application, so we should transfer from chain
            self.runtime.borrow_mut().transfer_combined(
                None,
                Account {
                    chain_id: swap_creator_chain,
                    owner: AccountOwner::from(swap_application_id),
                },
                liquidity.native_amount,
            );
        }

        // We fund swap application here but the funds will be process in this block, so we should
        // call swap application in next block
        // TODO: remove after https://github.com/linera-io/linera-protocol/issues/3486 being fixed
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(destination, MemeMessage::LiquidityFunded);

        Some(outcome)
    }

    pub async fn instantiate(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let _ = self.runtime.borrow_mut().application_parameters();

        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        // Signer should be the same as the creator
        assert!(
            self.runtime.borrow_mut().creator_signer() == signer,
            "Invalid owner"
        );

        let creator = self.runtime.borrow_mut().creator();
        let application = self.runtime.borrow_mut().application_account();

        self.argument.meme.virtual_initial_liquidity =
            self.runtime.borrow_mut().virtual_initial_liquidity();
        self.argument.meme.initial_liquidity = self.runtime.borrow_mut().initial_liquidity();

        let enable_mining = self.runtime.borrow_mut().enable_mining();
        let mining_supply = self.runtime.borrow_mut().mining_supply();
        let now = self.runtime.borrow_mut().system_time();

        self.state
            .instantiate(
                creator,
                application,
                self.argument.clone(),
                enable_mining,
                mining_supply,
                now,
            )
            .map_err(Into::into)?;

        // Let creator hold one hundred tokens for easy test
        let initial_owner_balance = self.state.initial_owner_balance();
        self.state
            .mint(creator, initial_owner_balance)
            .await
            .map_err(Into::into)?;
        let liquidity = self.runtime.borrow_mut().initial_liquidity();

        if let Some(liquidity) = liquidity {
            let swap_creator_chain = self.runtime.borrow_mut().swap_creator_chain_id();
            self.state
                .initialize_liquidity(liquidity, swap_creator_chain, enable_mining, mining_supply)
                .await
                .map_err(Into::into)?;
        }

        self.register_application();
        self.register_logo();

        // When the meme application is created, initial liquidity allowance should already be approved
        Ok(self.create_liquidity_pool())
    }
}
