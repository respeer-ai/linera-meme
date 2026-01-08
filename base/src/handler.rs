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
pub struct HandlerOutcome<M: Serialize, R: Serialize> {
    pub messages: Vec<HandlerMessage<M>>,
    pub response: Option<R>,
}

impl<M: Serialize, R: Serialize> HandlerOutcome<M, R> {
    pub fn new() -> Self {
        Self {
            messages: Vec::new(),
            response: None,
        }
    }

    pub fn with_message(&mut self, destination: ChainId, message: M) -> &mut Self {
        self.messages
            .push(HandlerMessage::new(destination, message));
        self
    }

    pub fn with_response(&mut self, response: R) -> &mut Self {
        self.response = Some(response);
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

    #[error("Not enabled")]
    NotEnabled,

    #[error("Invalid application response")]
    InvalidApplicationResponse,
}

#[async_trait(?Send)]
pub trait Handler<M: Serialize, R: Serialize> {
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<M, R>>, HandlerError>;
}
