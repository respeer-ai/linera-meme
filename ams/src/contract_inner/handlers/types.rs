use abi::ams::AmsMessage;

#[derive(Debug, Default)]
pub struct HandlerOutcome {
    pub messages: Vec<AmsMessage>,
}
