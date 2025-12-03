pub trait AccessControl {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn only_application_creator(&mut self) -> Result<(), Self::Error>;
}
