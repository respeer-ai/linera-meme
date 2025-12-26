use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, PoolState},
    FundRequest,
};
use abi::swap::{
    pool::{InstantiationArgument, Pool, PoolParameters},
    transaction::{Transaction, TransactionType},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, Timestamp};

#[async_trait(?Send)]
impl StateInterface for PoolState {
    type Error = StateError;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        parameters: PoolParameters,
        owner: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error> {
        self.pool.set(Some(Pool::create(
            parameters.token_0,
            parameters.token_1,
            argument.pool_fee_percent_mul_100,
            argument.protocol_fee_percent_mul_100,
            owner,
            block_timestamp,
        )));

        let mut pool = self.pool();

        self.router_application_id
            .set(Some(argument.router_application_id));
        self.transfer_id.set(1000);

        let mut liquidity = Amount::ZERO;

        if argument.amount_0 > Amount::ZERO && argument.amount_1 > Amount::ZERO {
            if !parameters.virtual_initial_liquidity {
                liquidity = self
                    .mint_shares(argument.amount_0, argument.amount_1, owner)
                    .await?;
            }
            pool.liquid(argument.amount_0, argument.amount_1, block_timestamp);
        }

        self.pool.set(Some(pool));
        self.transaction_id.set(1000);

        Ok(liquidity)
    }

    fn pool(&self) -> Pool {
        self.pool.get().as_ref().unwrap().clone()
    }

    fn router_application_id(&self) -> ApplicationId {
        self.router_application_id.get().unwrap()
    }

    fn reserve_0(&self) -> Amount {
        self.pool().reserve_0
    }

    fn reserve_1(&self) -> Amount {
        self.pool().reserve_1
    }

    fn consume_transfer_id(&mut self) -> u64 {
        let transfer_id = *self.transfer_id.get();
        self.transfer_id.set(transfer_id + 1);
        transfer_id
    }

    fn create_fund_request(&mut self, fund_request: FundRequest) -> Result<u64, Self::Error> {
        let transfer_id = self.consume_transfer_id();
        self.fund_requests.insert(&transfer_id, fund_request)?;
        Ok(transfer_id)
    }

    async fn fund_request(&self, transfer_id: u64) -> Result<FundRequest, Self::Error> {
        Ok(self.fund_requests.get(&transfer_id).await?.unwrap())
    }

    async fn _fund_requests(&self) -> Result<Vec<FundRequest>, Self::Error> {
        Ok(self
            .fund_requests
            .index_values()
            .await?
            .into_iter()
            .map(|(_, v)| v)
            .collect())
    }

    async fn update_fund_request(
        &mut self,
        transfer_id: u64,
        fund_request: FundRequest,
    ) -> Result<(), Self::Error> {
        let _ = self.fund_requests.get(&transfer_id).await?.unwrap();
        Ok(self.fund_requests.insert(&transfer_id, fund_request)?)
    }

    fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, Self::Error> {
        Ok(self.pool().calculate_swap_amount_0(amount_1)?)
    }

    fn calculate_swap_amount_1(&self, amount_0: Amount) -> Result<Amount, Self::Error> {
        Ok(self.pool().calculate_swap_amount_1(amount_0)?)
    }

    fn calculate_adjusted_amount_pair(
        &self,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(Amount, Amount), Self::Error> {
        Ok(self
            .pool()
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out)?)
    }

    fn try_calculate_swap_amount_pair(
        &self,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error> {
        Ok(self.pool().try_calculate_swap_amount_pair(
            amount_0_desired,
            amount_1_desired,
            amount_0_min,
            amount_1_min,
        )?)
    }

    fn try_calculate_liquidity_amount_pair(
        &self,
        liquidity: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error> {
        Ok(self.pool().try_calculate_liquidity_amount_pair(
            liquidity,
            *self.total_supply.get(),
            amount_0_min,
            amount_1_min,
        )?)
    }

    fn liquid(&mut self, balance_0: Amount, balance_1: Amount, block_timestamp: Timestamp) {
        let mut pool: Pool = self.pool();
        pool.liquid(balance_0, balance_1, block_timestamp);
        self.pool.set(Some(pool));
    }

    async fn add_liquidity(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error> {
        let liquidity = self.mint_shares(amount_0, amount_1, to).await?;

        let mut pool: Pool = self.pool();
        pool.liquid(
            pool.reserve_0.try_add(amount_0)?,
            pool.reserve_1.try_add(amount_1)?,
            block_timestamp,
        );
        self.pool.set(Some(pool));
        Ok(liquidity)
    }

    async fn liquidity(&self, account: Account) -> Result<Amount, Self::Error> {
        Ok(self.shares.get(&account).await?.unwrap_or(Amount::ZERO))
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        self.total_supply
            .set(self.total_supply.get().try_add(amount).unwrap());

        let share = self.liquidity(to).await?;
        Ok(self.shares.insert(&to, share.try_add(amount)?)?)
    }

    async fn burn(&mut self, from: Account, liquidity: Amount) -> Result<(), Self::Error> {
        self.total_supply
            .set(self.total_supply.get().try_sub(liquidity)?);

        let share = self.liquidity(from).await?;
        assert!(liquidity <= share, "Invalid liquidity");

        Ok(self.shares.insert(&from, share.try_sub(liquidity)?)?)
    }

    async fn mint_shares(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
    ) -> Result<Amount, Self::Error> {
        assert!(amount_0 > Amount::ZERO, "Invalid amount");
        assert!(amount_1 > Amount::ZERO, "Invalid amount");

        let pool = self.pool();
        let total_supply = *self.total_supply.get();

        let fee_share = pool.mint_fee(total_supply);
        self.mint(pool.fee_to, fee_share).await?;

        let liquidity = pool.calculate_liquidity(total_supply, amount_0, amount_1);
        self.mint(to, liquidity).await?;

        Ok(liquidity)
    }

    fn calculate_liquidity(&self, amount_0: Amount, amount_1: Amount) -> Amount {
        let total_supply = *self.total_supply.get();
        self.pool()
            .calculate_liquidity(total_supply, amount_0, amount_1)
    }

    fn set_fee_to(&mut self, operator: Account, account: Account) {
        let mut pool = self.pool();

        assert!(pool.fee_to_setter == operator, "Invalid operator");
        pool.fee_to = account;

        self.pool.set(Some(pool));
    }

    fn set_fee_to_setter(&mut self, operator: Account, account: Account) {
        let mut pool = self.pool();

        assert!(pool.fee_to_setter == operator, "Invalid operator");
        pool.fee_to_setter = account;

        self.pool.set(Some(pool));
    }

    fn calculate_price_pair(&self) -> (Amount, Amount) {
        self.pool().calculate_price_pair()
    }

    fn build_transaction(
        &self,
        owner: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out: Option<Amount>,
        amount_1_out: Option<Amount>,
        liquidity: Option<Amount>,
        timestamp: Timestamp,
    ) -> Transaction {
        let transaction_type =
            if amount_0_in.is_some() && amount_1_in.is_some() && liquidity.is_some() {
                TransactionType::AddLiquidity
            } else if amount_0_out.is_some() && amount_1_out.is_some() && liquidity.is_some() {
                TransactionType::RemoveLiquidity
            } else if amount_0_in.is_some() && amount_1_out.is_some() {
                TransactionType::SellToken0
            } else if amount_0_out.is_some() && amount_1_in.is_some() {
                TransactionType::BuyToken0
            } else {
                unreachable!();
            };

        Transaction {
            transaction_id: None,
            transaction_type,
            from: owner,
            amount_0_in,
            amount_1_in,
            amount_0_out,
            amount_1_out,
            liquidity,
            created_at: timestamp,
        }
    }

    fn create_transaction(&mut self, mut transaction: Transaction) -> Transaction {
        let transaction_id = *self.transaction_id.get();

        transaction.transaction_id = Some(transaction_id);
        self.latest_transactions.push_back(transaction.clone());

        const MAX_LAST_TRANSACTIONS: usize = 5000;

        if self.latest_transactions.count() > MAX_LAST_TRANSACTIONS {
            self.latest_transactions.delete_front();
        }
        self.transaction_id.set(transaction_id + 1);

        transaction
    }
}
