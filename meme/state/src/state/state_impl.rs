use abi::meme::{HandoffArgument, InitializeArgument, Liquidity, MiningInfo, StateInstantiationArgument};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId};
use std::collections::HashMap;

use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, MemeState},
};

#[async_trait(?Send)]
impl StateInterface for MemeState {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.business_application_id
            .set(Some(argument.business_application_id));
        self.operator.set(argument.operator);
        self.proxy_application_id
            .set(argument.proxy_application_id);
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn handoff(&mut self, argument: HandoffArgument) -> Result<(), Self::Error> {
        self.business_application_id
            .set(Some(argument.new_business_application_id));
        if let Some(proxy_application_id) = argument.new_proxy_application_id {
            self.proxy_application_id.set(Some(proxy_application_id));
        }
        if let Some(swap_application_id) = argument.new_swap_application_id {
            self.swap_application_id.set(Some(swap_application_id));
        }
        if let Some(ams_application_id) = argument.new_ams_application_id {
            self.ams_application_id.set(Some(ams_application_id));
        }
        if let Some(blob_gateway_application_id) = argument.new_blob_gateway_application_id {
            self.blob_gateway_application_id
                .set(Some(blob_gateway_application_id));
        }
        Ok(())
    }

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.operator.get().ok_or(StateError::OperatorNotInitialized)
    }

    async fn owner(&self) -> Result<Account, Self::Error> {
        self.owner.get().ok_or(StateError::OwnerNotInitialized)
    }

    async fn balance_of(&self, owner: Account) -> Result<Amount, Self::Error> {
        Ok(self.balances.get(&owner).await?.unwrap_or(Amount::ZERO))
    }

    async fn transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        if amount == Amount::ZERO {
            return Err(StateError::InvalidAmount);
        }
        if from == to {
            return Err(StateError::SelfTransfer);
        }

        let from_balance = self.balance_of(from).await?;
        if from_balance < amount {
            return Err(StateError::InsufficientFunds);
        }

        let to_balance = self
            .balance_of(to)
            .await?
            .try_add(amount)
            .map_err(|_| StateError::BalanceOverflow)?;

        self.balances.insert(
            &from,
            from_balance
                .try_sub(amount)
                .map_err(|_| StateError::InvalidAmount)?,
        )?;
        self.balances.insert(&to, to_balance)?;

        Ok(())
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Result<Amount, Self::Error> {
        Ok(self
            .allowances
            .get(&owner)
            .await?
            .and_then(|allowances| allowances.get(&spender).copied())
            .unwrap_or(Amount::ZERO))
    }

    async fn transfer_from(
        &mut self,
        origin: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        if amount == Amount::ZERO {
            return Err(StateError::InvalidAmount);
        }
        if from == to {
            return Err(StateError::SelfTransfer);
        }

        let allowance = self.allowance_of(from, origin).await?;
        if allowance < amount {
            return Err(StateError::InsufficientAllowance);
        }

        let to_balance = self
            .balance_of(to)
            .await?
            .try_add(amount)
            .map_err(|_| StateError::BalanceOverflow)?;

        self.balances.insert(&to, to_balance)?;

        let mut allowances = self
            .allowances
            .get(&from)
            .await?
            .unwrap_or(HashMap::new());
        let new_allowance = allowance.try_sub(amount).map_err(|_| StateError::InvalidAmount)?;
        allowances.insert(origin, new_allowance);
        self.allowances.insert(&from, allowances)?;

        Ok(())
    }

    async fn approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        if owner == spender {
            return Err(StateError::InvalidOwner);
        }
        // Approve application balance to meme creator is not allowed
        if owner == self.holder.get().unwrap() && spender == self.owner.get().unwrap() {
            return Err(StateError::InvalidOwner);
        }

        let owner_balance = self.balance_of(owner).await?;
        if owner_balance < amount {
            return Err(StateError::InsufficientFunds);
        }

        let mut allowances = self
            .allowances
            .get(&owner)
            .await?
            .unwrap_or(HashMap::new());
        let spender_allowance = allowances
            .get(&spender)
            .copied()
            .unwrap_or(Amount::ZERO)
            .try_add(amount)
            .map_err(|_| StateError::BalanceOverflow)?;

        self.balances.insert(
            &owner,
            owner_balance
                .try_sub(amount)
                .map_err(|_| StateError::InvalidAmount)?,
        )?;
        allowances.insert(spender, spender_allowance);
        self.allowances.insert(&owner, allowances)?;

        Ok(())
    }

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error> {
        if self.owner.get().is_some() {
            return Err(StateError::AlreadyInitialized);
        }

        self.owner.set(Some(argument.owner));
        self.holder.set(Some(argument.holder));
        self.meme.set(Some(argument.meme.clone()));
        self.initial_owner_balance.set(argument.initial_owner_balance);

        self.balances
            .insert(&argument.holder, argument.meme.initial_supply)?;

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.swap_application_id.set(argument.swap_application_id);

        if argument.enable_mining {
            let mining_supply = argument
                .mining_supply
                .unwrap_or(argument.meme.initial_supply);
            self.mining_info
                .set(Some(MiningInfo::new(mining_supply, argument.now)));
        }

        Ok(())
    }

    async fn initialize_liquidity(
        &mut self,
        liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> Result<(), Self::Error> {
        self.initialize_liquidity_internal(
            liquidity,
            swap_creator_chain_id,
            enable_mining,
            mining_supply,
        )
        .await
    }

    async fn initial_liquidity(&self) -> Result<Option<Liquidity>, Self::Error> {
        Ok(self.initial_liquidity.get().clone())
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        let holder = self.holder.get().ok_or(StateError::InvalidOwner)?;
        self.transfer(holder, to, amount).await
    }

    async fn transfer_ownership(
        &mut self,
        owner: Account,
        new_owner: Account,
    ) -> Result<(), Self::Error> {
        let current_owner = self.owner.get().ok_or(StateError::OwnerNotInitialized)?;
        if owner != current_owner {
            return Err(StateError::InvalidOwner);
        }
        self.owner.set(Some(new_owner));
        Ok(())
    }

    async fn mining_info(&self) -> Result<MiningInfo, Self::Error> {
        self.mining_info
            .get()
            .clone()
            .ok_or(StateError::MiningInfoNotInitialized)
    }

    async fn mining_reward(
        &mut self,
        owner: Account,
        reward_amount: Amount,
        mining_info: MiningInfo,
    ) -> Result<(), Self::Error> {
        self.mint(owner, reward_amount).await?;
        self.mining_info.set(Some(mining_info));
        Ok(())
    }

    async fn swap_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        Ok(self.swap_application_id.get().clone())
    }

    async fn proxy_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        Ok(self.proxy_application_id.get().clone())
    }

    async fn start_mining(&mut self) -> Result<(), Self::Error> {
        let mut mining_info = self.mining_info().await?;
        mining_info.mining_started = true;
        self.mining_info.set(Some(mining_info));
        Ok(())
    }
}

impl MemeState {
    async fn initialize_liquidity_internal(
        &mut self,
        mut liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> Result<(), StateError> {
        assert!(
            liquidity.fungible_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );
        assert!(
            liquidity.native_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );

        let holder = self.holder.get().ok_or(StateError::InvalidOwner)?;
        let holder_balance = self.balance_of(holder).await?;

        let mining_supply = if enable_mining {
            mining_supply.unwrap_or(holder_balance)
        } else {
            Amount::ZERO
        };

        if holder_balance < liquidity.fungible_amount || holder_balance < mining_supply {
            return Err(StateError::InsufficientFunds);
        }

        let max_liquidity_amount = holder_balance.saturating_sub(mining_supply);
        if enable_mining && liquidity.fungible_amount > max_liquidity_amount {
            liquidity.fungible_amount = max_liquidity_amount;
        }

        if liquidity.fungible_amount <= Amount::ZERO {
            return Ok(());
        }

        self.initial_liquidity.set(Some(liquidity.clone()));

        let swap_application_id = self
            .swap_application_id
            .get()
            .ok_or(StateError::NotExists)?;
        let spender = Account {
            chain_id: swap_creator_chain_id,
            owner: AccountOwner::from(swap_application_id),
        };
        self.approve(holder, spender, liquidity.fungible_amount).await
    }
}
