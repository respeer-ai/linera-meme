use super::StateContract;
use abi::state::{StateOperation, StateResponse};

impl StateContract {
    pub async fn on_operation(&mut self, _operation: StateOperation) -> StateResponse {
        unimplemented!("state operation behavior is implemented in GSTATE-004")
    }
}
