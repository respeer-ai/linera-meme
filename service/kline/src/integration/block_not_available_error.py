class BlockNotAvailableError(RuntimeError):
    """Raised when the requested chain height is not yet available on the node service."""
