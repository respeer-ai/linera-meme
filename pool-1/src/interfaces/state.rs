use crate::FundRequest;
use abi::swap::{
    pool::{InstantiationArgument, Pool, PoolParameters},
    transaction::Transaction,
};
use async_trait::async_trait;
use base::handler::HandlerError;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, Timestamp};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + Into<HandlerError> + 'static;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        parameters: PoolParameters,
        owner: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error>;

    fn pool(&self) -> Pool;

    fn router_application_id(&self) -> ApplicationId;

    fn reserve_0(&self) -> Amount;
    fn reserve_1(&self) -> Amount;

    fn consume_transfer_id(&mut self) -> u64;

    fn create_fund_request(&mut self, fund_request: FundRequest) -> Result<u64, Self::Error>;

    async fn fund_request(&self, transfer_id: u64) -> Result<FundRequest, Self::Error>;

    async fn _fund_requests(&self) -> Result<Vec<FundRequest>, Self::Error>;

    async fn update_fund_request(
        &mut self,
        transfer_id: u64,
        fund_request: FundRequest,
    ) -> Result<(), Self::Error>;

    fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, Self::Error>;
    fn calculate_swap_amount_1(&self, amount_0: Amount) -> Result<Amount, Self::Error>;

    fn calculate_adjusted_amount_pair(
        &self,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(Amount, Amount), Self::Error>;

    fn try_calculate_swap_amount_pair(
        &self,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error>;

    fn try_calculate_liquidity_amount_pair(
        &self,
        liquidity: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error>;

    fn liquid(&mut self, balance_0: Amount, balance_1: Amount, block_timestamp: Timestamp);

    async fn add_liquidity(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error>;

    async fn liquidity(&self, account: Account) -> Result<Amount, Self::Error>;

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn burn(&mut self, from: Account, liquidity: Amount) -> Result<(), Self::Error>;

    async fn mint_shares(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
    ) -> Result<Amount, Self::Error>;

    fn calculate_liquidity(&self, amount_0: Amount, amount_1: Amount) -> Amount;

    fn set_fee_to(&mut self, operator: Account, account: Account);

    fn set_fee_to_setter(&mut self, operator: Account, account: Account);

    fn calculate_price_pair(&self) -> (Amount, Amount);

    fn build_transaction(
        &self,
        owner: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out: Option<Amount>,
        amount_1_out: Option<Amount>,
        liquidity: Option<Amount>,
        timestamp: Timestamp,
    ) -> Transaction;

    fn create_transaction(&mut self, transaction: Transaction) -> Transaction;
}
