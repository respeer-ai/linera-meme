#![cfg(not(target_arch = "wasm32"))]

use abi::state::{StateAbi, StateOperation};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner},
    test::{ActiveChain, TestValidator},
};

fn chain_owner_account(chain: &ActiveChain) -> Account {
    Account {
        chain_id: chain.id(),
        owner: AccountOwner::from(chain.public_key()),
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn set_operator_operation_from_operator_chain_routes_to_state_creator_chain() {
    let (validator, state_bytecode_id) =
        TestValidator::with_current_module::<StateAbi, (), ()>().await;
    let mut state_creator_chain = validator.new_chain().await;
    let operator_chain = validator.new_chain().await;
    let new_operator_chain = validator.new_chain().await;

    let state_application_id = state_creator_chain
        .create_application::<StateAbi, (), ()>(state_bytecode_id, (), (), vec![])
        .await;
    let new_operator = chain_owner_account(&new_operator_chain);

    let (certificate, _) = operator_chain
        .add_block(|block| {
            block.with_operation(
                state_application_id,
                StateOperation::SetOperator {
                    application_id: state_application_id.forget_abi(),
                    new_operator,
                },
            );
        })
        .await;

    let routed_message_count = certificate
        .message_bundles_for(state_creator_chain.id())
        .map(|(_, bundle)| bundle.messages.len())
        .sum::<usize>();
    assert_eq!(routed_message_count, 1);
}
