use super::MemeContract;
use std::{cell::RefCell, rc::Rc};

use abi::{
    ams::{AmsAbi, AmsOperation, Metadata, MEME},
    blob_gateway::{BlobDataType, BlobGatewayAbi, BlobGatewayOperation},
    meme::{InstantiationArgument, MemeMessage, MemeOperation, MemeResponse},
    policy::open_chain_fee_budget,
};

use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use meme::{
    contract_inner::handlers::HandlerFactory,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    state::adapter::StateAdapter,
};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};

impl MemeContract {
    fn register_logo(&mut self) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());

        if let Some(blob_gateway_application_id) = self.state.borrow().blob_gateway_application_id()
        {
            let call = BlobGatewayOperation::Register {
                store_type: self.state.borrow().logo_store_type(),
                data_type: BlobDataType::Image,
                blob_hash: self.state.borrow().logo(),
            };

            log::info!("DEBUG MEME: registering meme logo ... {:?}", call);

            let _ = runtime_context.call_application(
                blob_gateway_application_id.with_abi::<BlobGatewayAbi>(),
                &call,
            );
        }
    }

    fn register_application(&mut self) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());
        let application_id = runtime_context.application_id().forget_abi();
        let created_at = runtime_context.system_time();
        let creator = runtime_context.creator();

        if let Some(ams_application_id) = self.state.borrow().ams_application_id() {
            let call = AmsOperation::Register {
                metadata: Metadata {
                    creator,
                    application_name: self.state.borrow().name(),
                    application_id,
                    application_type: MEME.to_string(),
                    key_words: vec![
                        "Linera".to_string(),
                        "Meme".to_string(),
                        "PoW microchain".to_string(),
                    ],
                    logo_store_type: self.state.borrow().logo_store_type(),
                    logo: self.state.borrow().logo(),
                    description: self.state.borrow().description(),
                    twitter: self.state.borrow().twitter(),
                    telegram: self.state.borrow().telegram(),
                    discord: self.state.borrow().discord(),
                    website: self.state.borrow().website(),
                    github: self.state.borrow().github(),
                    spec: Some(
                        serde_json::to_string(&self.state.borrow().meme())
                            .expect("Failed serialize meme"),
                    ),
                    created_at,
                },
            };

            log::info!("DEBUG MEME: registering meme ... {:?}", call);

            let _ =
                runtime_context.call_application(ams_application_id.with_abi::<AmsAbi>(), &call);
        }
    }

    fn create_liquidity_pool(&mut self) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());

        log::info!("DEBUG MEME: creating liquidity pool ...");

        let Some(swap_application_id) = self.state.borrow().swap_application_id() else {
            log::info!(
                "DEBUG MEME: ignore creating liquidity pool for invalid swap application id"
            );
            return;
        };
        let Some(liquidity) = runtime_context.initial_liquidity() else {
            log::info!("DEBUG MEME: ignore creating liquidity pool for invalid initial liquidity");
            return;
        };
        if liquidity.fungible_amount <= Amount::ZERO || liquidity.native_amount <= Amount::ZERO {
            log::info!(
                "DEBUG MEME: ignore creating liquidity pool for fungible amount {}, native amount {}",
                liquidity.fungible_amount,
                liquidity.native_amount,
            );
            return;
        }

        // Meme chain will be created by swap creator chain, so we fund signer on swap creator
        // chain then it'll fund meme chain
        let swap_creator_chain = runtime_context.swap_creator_chain_id();
        runtime_context.transfer_combined(
            None,
            Account {
                chain_id: swap_creator_chain,
                owner: AccountOwner::CHAIN,
            },
            open_chain_fee_budget(),
        );
        if !runtime_context.virtual_initial_liquidity() {
            // At this moment (instantiating) there is no balance on application, so we should transfer from chain
            runtime_context.transfer_combined(
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
        let application_creator_chain_id = runtime_context.application_creator_chain_id();
        runtime_context.send_message(application_creator_chain_id, MemeMessage::LiquidityFunded);
    }

    pub async fn _instantiate(&mut self, mut instantiation_argument: InstantiationArgument) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());

        let _ = runtime_context.application_parameters();

        let signer = runtime_context.authenticated_signer().unwrap();
        // Signer should be the same as the creator
        assert!(runtime_context.creator_signer() == signer, "Invalid owner");

        let creator = runtime_context.creator();
        let application = runtime_context.application_account();

        instantiation_argument.meme.virtual_initial_liquidity =
            runtime_context.virtual_initial_liquidity();
        instantiation_argument.meme.initial_liquidity = runtime_context.initial_liquidity();

        self.state
            .borrow_mut()
            .instantiate(creator, application, instantiation_argument)
            .expect("Failed instantiate");

        // Let creator hold one hundred tokens for easy test
        let initial_owner_balance = self.state.borrow().initial_owner_balance();
        self.state
            .borrow_mut()
            .mint(creator, initial_owner_balance)
            .await
            .expect("Failed initialize balance");

        if let Some(liquidity) = runtime_context.initial_liquidity() {
            let swap_creator_chain = runtime_context.swap_creator_chain_id();
            self.state
                .borrow_mut()
                .initialize_liquidity(liquidity, swap_creator_chain)
                .await
                .expect("Failed initialize liquidity");
        }

        self.register_application();
        self.register_logo();

        // When the meme application is created, initial liquidity allowance should already be approved
        self.create_liquidity_pool()
    }

    pub async fn on_op(&mut self, op: &MemeOperation) -> MemeResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));

        let state_adapter = StateAdapter::new(self.state.clone());

        log::warn!("DEBUG OP:SWAP: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return MemeResponse::Ok,
                Err(err) => panic!("Failed OP {:?}: {err}", op),
            };

        log::warn!("DEBUG OP:SWAP: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::warn!("DEBUG OP:SWAP: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        outcome.response.unwrap_or(MemeResponse::Ok)
    }

    pub async fn on_message(&mut self, msg: &MemeMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::warn!("DEBUG MSG:SWAP: processing {:?}", msg);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, None, Some(msg))
                .expect("Failed: construct message handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return,
                Err(err) => panic!("Failed MSG {:?}: {err}", msg),
            };

        log::warn!("DEBUG MSG:SWAP: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            log::warn!("DEBUG MSG:SWAP: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
