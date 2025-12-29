use async_trait::async_trait;
use linera_sdk::{
    linera_base_types::{ArithmeticError, ChainId},
    views::ViewError,
};
use serde::Serialize;
use thiserror::Error;

// TODO: support send to stream
#[derive(Debug)]
pub struct HandlerMessage<M: Serialize> {
    destination: ChainId,
    message: M,
}

impl<M: Serialize> HandlerMessage<M> {
    pub fn new(destination: ChainId, message: M) -> Self {
        Self {
            destination,
            message,
        }
    }

    pub fn destination(&self) -> &ChainId {
        &self.destination
    }

    pub fn message(&self) -> &M {
        &self.message
    }
}

#[derive(Debug, Default)]
pub struct HandlerOutcome<M: Serialize> {
    pub messages: Vec<HandlerMessage<M>>,
}

impl<M: Serialize> HandlerOutcome<M> {
    pub fn new() -> Self {
        Self {
            messages: Vec::new(),
        }
    }

    pub fn with_message(&mut self, destination: ChainId, message: M) -> &mut Self {
        self.messages
            .push(HandlerMessage::new(destination, message));
        self
    }
}

#[derive(Debug, Error)]
pub enum HandlerError {
    #[error("Invalid operation and message")]
    InvalidOperationAndMessage,

    #[error("Not implemented")]
    NotImplemented,

    #[error("Not allowed")]
    NotAllowed,

    #[error(transparent)]
    RuntimeError(Box<dyn std::error::Error>),

    #[error(transparent)]
    ProcessError(Box<dyn std::error::Error>),

    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Insufficient funds")]
    InsufficientFunds,
}

#[async_trait(?Send)]
pub trait Handler<M: Serialize> {
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<M>>, HandlerError>;
}
