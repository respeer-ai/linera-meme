use super::super::MemeStateContract;
use abi::meme::{
    state_v1::{
        InitializeArgument, MemeStateAbi, MemeStateV1Operation, MemeStateV1Response,
        StateInstantiationArgument,
    },
    Liquidity, Meme, Metadata,
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationDescription, ApplicationId, BlockHeight,
        ChainId, CryptoHash, ModuleId, TestString, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use meme_state::state::MemeState;
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    contract: MemeStateContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = Self::runtime();
        let mut contract = MemeStateContract {
            state: Rc::new(RefCell::new(
                MemeState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to load meme state v1"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };
        contract
            .instantiate(StateInstantiationArgument {
                business_application_id: Self::business_application_id(),
                operator: Some(Self::operator()),
                proxy_application_id: Some(Self::business_application_id()),
            })
            .blocking_wait();
        Self { contract }
    }

    async fn execute_operation(
        &mut self,
        operation: MemeStateV1Operation,
    ) -> MemeStateV1Response {
        self.contract.execute_operation(operation).await
    }

    fn set_chain_id(&mut self, chain_id: ChainId) {
        self.contract.runtime.borrow_mut().set_chain_id(chain_id);
    }

    fn set_application_creator_chain_id(&mut self, chain_id: ChainId) {
        self.contract
            .runtime
            .borrow_mut()
            .set_application_creator_chain_id(chain_id);
    }

    fn runtime() -> ContractRuntime<MemeStateContract> {
        ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_caller_id(Self::business_application_id())
            .with_chain_id(Self::chain_id())
            .with_application_creator_chain_id(Self::chain_id())
            .with_application_description(
                Self::business_application_id(),
                Self::application_description(Self::chain_id()),
            )
            .with_application_description(
                Self::swap_application_id(),
                Self::application_description(Self::chain_id()),
            )
            .with_application_id(Self::state_application_id().with_abi::<MemeStateAbi>())
            .with_system_time(Timestamp::from(1))
            .with_block_height(BlockHeight::from(1))
    }

    fn application_description(creator_chain_id: ChainId) -> ApplicationDescription {
        ApplicationDescription {
            module_id: ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap(),
            creator_chain_id,
            block_height: BlockHeight::from(1),
            application_index: 0,
            parameters: Vec::new(),
            required_application_ids: Vec::new(),
        }
    }

    fn operator() -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        }
    }

    fn chain_id() -> ChainId {
        ChainId(
            CryptoHash::from_str(
                "a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa",
            )
            .unwrap(),
        )
    }

    fn other_chain_id() -> ChainId {
        ChainId(
            CryptoHash::from_str(
                "a20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa",
            )
            .unwrap(),
        )
    }

    fn business_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn swap_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
    }

    fn state_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
    }

    fn application_id(hex: &str) -> ApplicationId {
        ApplicationId::from_str(hex).unwrap()
    }

    fn meme() -> Meme {
        Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply: Amount::from_tokens(21000000),
            total_supply: Amount::from_tokens(21000000),
            metadata: Metadata {
                logo_store_type: abi::store_type::StoreType::S3,
                logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                description: "Test token description".to_string(),
                twitter: None,
                telegram: None,
                discord: None,
                website: None,
                github: None,
                live_stream: None,
            },
            virtual_initial_liquidity: true,
            initial_liquidity: Some(Liquidity {
                fungible_amount: Amount::from_tokens(11000000),
                native_amount: Amount::from_tokens(10),
            }),
        }
    }

    fn initialize_argument() -> InitializeArgument {
        InitializeArgument {
            owner: Self::operator(),
            holder: Account {
                chain_id: Self::chain_id(),
                owner: AccountOwner::from(Self::business_application_id()),
            },
            meme: Self::meme(),
            initial_owner_balance: Amount::from_tokens(100),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: Some(Self::swap_application_id()),
            enable_mining: true,
            mining_supply: None,
            now: Timestamp::now(),
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn start_mining_succeeds_on_creator_chain() {
    let mut suite = TestSuite::new();
    suite
        .execute_operation(MemeStateV1Operation::Initialize {
            argument: TestSuite::initialize_argument(),
        })
        .await;

    let response = suite.execute_operation(MemeStateV1Operation::StartMining).await;
    assert_eq!(response, MemeStateV1Response::Ok);
}

#[tokio::test(flavor = "multi_thread")]
async fn start_mining_rejects_non_creator_chain() {
    let mut suite = TestSuite::new();
    suite.set_chain_id(TestSuite::other_chain_id());
    suite.set_application_creator_chain_id(TestSuite::chain_id());
    suite
        .execute_operation(MemeStateV1Operation::Initialize {
            argument: TestSuite::initialize_argument(),
        })
        .await;

    let response = suite.execute_operation(MemeStateV1Operation::StartMining).await;
    assert!(matches!(response, MemeStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn initial_liquidity_returns_none_before_liquidity_initialized() {
    let mut suite = TestSuite::new();
    suite
        .execute_operation(MemeStateV1Operation::Initialize {
            argument: TestSuite::initialize_argument(),
        })
        .await;

    let response = suite
        .execute_operation(MemeStateV1Operation::InitialLiquidity)
        .await;
    assert_eq!(response, MemeStateV1Response::InitialLiquidity(None));
}
