    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        // TODO: if AccountOwner exists, reject
        assert!(
            !self.genesis_miners.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self
            .genesis_miners
            .insert(&owner, GenesisMiner { owner, approval })?)
    }

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        let mut miner = self.genesis_miners.get(&owner).await?.unwrap();
        assert!(!miner.approval.voted(operator), "Already voted");
        miner.approval.approve(operator);
        Ok(self.genesis_miners.insert(&owner, miner)?)
    }

    async fn genesis_miners(&self) -> Result<Vec<Miner>, StateError> {
        let mut miners = Vec::new();
        self.genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approved() {
                    miners.push(Miner {
                        owner,
                        registered_at: 0.into(),
                    });
                }
                Ok(())
            })
            .await?;
        Ok(miners)
    }

