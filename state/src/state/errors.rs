use linera_sdk::linera_base_types::ApplicationId;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("operator is already initialized")]
    OperatorAlreadyInitialized,

    #[error("operator is not initialized")]
    OperatorNotInitialized,

    #[error("namespace management is frozen")]
    NamespaceManagementFrozen,

    #[error("application {0:?} is already bound to the namespace")]
    ApplicationAlreadyBound(ApplicationId),

    #[error("namespace {0} does not exist")]
    NamespaceNotFound(u8),

    #[error("application {application_id:?} is not bound to namespace {namespace}")]
    ApplicationNotBound {
        namespace: u8,
        application_id: ApplicationId,
    },

    #[error("handoff target {0:?} is already bound to the namespace")]
    HandoffTargetAlreadyBound(ApplicationId),

    #[error("namespace {0} has no available slots")]
    NamespaceFull(u8),

    #[error("namespace {namespace} has an invalid slot index {slot}")]
    NamespaceSlotOverflow { namespace: u8, slot: usize },
}
