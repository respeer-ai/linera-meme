        Ok(())
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, StateError> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), StateError> {
        self.business_application_id
            .set(Some(new_business_application_id));
        Ok(())
    }

    async fn operator(&mut self) -> Result<Account, StateError> {
        self.operator
            .get()
            .ok_or(StateError::OperatorNotInitialized)
    }

    async fn initial_approval(&self) -> Result<Approval, StateError> {
        let operators = self.operators.count().await?;
        Ok(Approval::new(std::cmp::max(operators * 2 / 3, 1)))
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        // TODO: if AccountOwner exists, reject
        assert!(
            !self.genesis_miners.contains_key(&owner).await?,
