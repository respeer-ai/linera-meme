use abi::AmsMessage;

#[derive(Debug, Default)]
pub struct HandlerOutcome {
    pub messages: Vec<AmsMessage>,
}
