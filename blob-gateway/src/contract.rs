// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    blob_gateway::{
        BlobData, BlobDataType, BlobGatewayAbi, BlobGatewayMessage, BlobGatewayOperation,
        BlobGatewayResponse,
    },
    store_type::StoreType,
};
use blob_gateway::BlobGatewayError;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, CryptoHash, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime, DataBlobHash,
};

use self::state::BlobGateway;

pub struct BlobGatewayContract {
    state: BlobGateway,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(BlobGatewayContract);

impl WithContractAbi for BlobGatewayContract {
    type Abi = BlobGatewayAbi;
}

impl Contract for BlobGatewayContract {
    type Message = BlobGatewayMessage;
    type InstantiationArgument = ();
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = BlobGateway::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        BlobGatewayContract { state, runtime }
    }

    async fn instantiate(&mut self, _value: ()) {}

    async fn execute_operation(&mut self, operation: BlobGatewayOperation) -> BlobGatewayResponse {
        match operation {
            BlobGatewayOperation::Register {
                store_type,
                data_type,
                blob_hash,
            } => self
                .on_op_register(store_type, data_type, blob_hash)
                .await
                .expect("Failed OP: Register"),
        }
    }

    async fn execute_message(&mut self, message: BlobGatewayMessage) {
        if self.runtime.chain_id() != self.runtime.application_creator_chain_id() {
            panic!("Messages can only be executed on creator chain");
        }
        match message {
            BlobGatewayMessage::Register {
                creator,
                store_type,
                data_type,
                blob_hash,
            } => self
                .on_msg_register(creator, store_type, data_type, blob_hash)
                .await
                .expect("Failed MSG: Register"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl BlobGatewayContract {
    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => Some(AccountOwner::User(owner)),
                _ => None,
            },
        }
    }

    async fn on_op_register(
        &mut self,
        store_type: StoreType,
        data_type: BlobDataType,
        blob_hash: CryptoHash,
    ) -> Result<BlobGatewayResponse, BlobGatewayError> {
        let creator = self.owner_account();
        self.runtime
            .prepare_message(BlobGatewayMessage::Register {
                creator,
                store_type,
                data_type,
                blob_hash,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(BlobGatewayResponse::Ok)
    }

    async fn on_msg_register(
        &mut self,
        creator: Account,
        store_type: StoreType,
        data_type: BlobDataType,
        blob_hash: CryptoHash,
    ) -> Result<(), BlobGatewayError> {
        let data_blob_hash = DataBlobHash(blob_hash);
        self.runtime.assert_data_blob_exists(data_blob_hash);

        match self.state.blobs.get(&blob_hash).await? {
            Some(_) => Ok(()),
            _ => Ok(self.state.blobs.insert(
                &blob_hash,
                BlobData {
                    store_type,
                    data_type,
                    blob_hash,
                    creator,
                    created_at: self.runtime.system_time(),
                },
            )?),
        }
    }
}
