use super::super::{BlobGatewayContract, BlobGatewayState};

use abi::{
    blob_gateway::{
        BlobData, BlobDataType, BlobGatewayAbi, BlobGatewayMessage, BlobGatewayOperation,
    },
    store_type::StoreType,
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, TestString, Timestamp},
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[tokio::test(flavor = "multi_thread")]
async fn op_register_queues_message_with_runtime_metadata() {
    let mut contract = create_and_instantiate_blob_gateway();
    let blob_hash = test_hash("blob-1");

    let response = contract
        .execute_operation(BlobGatewayOperation::Register {
            store_type: StoreType::S3,
            data_type: BlobDataType::Image,
            blob_hash,
        })
        .await;

    assert!(matches!(
        response,
        abi::blob_gateway::BlobGatewayResponse::Ok
    ));

    let runtime = contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();

    assert_eq!(requests.len(), 1);
    assert_eq!(requests[0].destination, creator_chain_id());
    match &requests[0].message {
        BlobGatewayMessage::Register { blob_data } => {
            assert_eq!(
                blob_data,
                &BlobData {
                    store_type: StoreType::S3,
                    data_type: BlobDataType::Image,
                    blob_hash,
                    creator: authenticated_account(),
                    created_at: Timestamp::from(1),
                }
            );
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_register_stores_blob_data() {
    let mut contract = create_and_instantiate_blob_gateway();
    let blob_data = test_blob_data(test_hash("blob-2"), StoreType::Ipfs, BlobDataType::Html);

    contract
        .execute_message(BlobGatewayMessage::Register {
            blob_data: blob_data.clone(),
        })
        .await;

    assert_eq!(
        contract
            .state
            .borrow()
            .blobs
            .get(&blob_data.blob_hash)
            .await
            .unwrap()
            .unwrap(),
        blob_data
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_register_duplicate_hash_is_idempotent_and_keeps_first_metadata() {
    let mut contract = create_and_instantiate_blob_gateway();
    let blob_hash = test_hash("blob-3");
    let first = test_blob_data(blob_hash, StoreType::S3, BlobDataType::Raw);
    let second = BlobData {
        store_type: StoreType::Ipfs,
        data_type: BlobDataType::Video,
        blob_hash,
        creator: other_account(),
        created_at: Timestamp::from(99),
    };

    contract
        .execute_message(BlobGatewayMessage::Register {
            blob_data: first.clone(),
        })
        .await;
    contract
        .execute_message(BlobGatewayMessage::Register { blob_data: second })
        .await;

    assert_eq!(
        contract
            .state
            .borrow()
            .blobs
            .get(&blob_hash)
            .await
            .unwrap()
            .unwrap(),
        first
    );
}

fn create_and_instantiate_blob_gateway() -> BlobGatewayContract {
    let runtime = ContractRuntime::new()
        .with_application_parameters(())
        .with_authenticated_signer(authenticated_account().owner)
        .with_chain_id(current_chain_id())
        .with_application_creator_chain_id(creator_chain_id())
        .with_system_time(Timestamp::from(1))
        .with_application_id(application_id());
    let mut contract = BlobGatewayContract {
        state: Rc::new(RefCell::new(
            BlobGatewayState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    contract.instantiate(()).blocking_wait();
    contract
}

fn authenticated_account() -> Account {
    Account {
        chain_id: current_chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap(),
    }
}

fn other_account() -> Account {
    Account {
        chain_id: current_chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e09",
        )
        .unwrap(),
    }
}

fn current_chain_id() -> ChainId {
    ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8").unwrap()
}

fn creator_chain_id() -> ChainId {
    ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65").unwrap()
}

fn application_id() -> ApplicationId<BlobGatewayAbi> {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
        .with_abi::<BlobGatewayAbi>()
}

fn test_hash(seed: &str) -> linera_sdk::linera_base_types::CryptoHash {
    linera_sdk::linera_base_types::CryptoHash::new(&TestString::new(seed.to_owned()))
}

fn test_blob_data(
    blob_hash: linera_sdk::linera_base_types::CryptoHash,
    store_type: StoreType,
    data_type: BlobDataType,
) -> BlobData {
    BlobData {
        store_type,
        data_type,
        blob_hash,
        creator: authenticated_account(),
        created_at: Timestamp::from(1),
    }
}
