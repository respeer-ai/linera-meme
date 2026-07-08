"""Exceptions raised by linest."""


class LinestError(Exception):
    """Base exception for all linest errors."""


class ConfigError(LinestError):
    """Raised when network configuration is missing or invalid."""


class RegistryError(LinestError):
    """Raised when the deployment registry is inconsistent or unreadable."""


class DeploymentError(LinestError):
    """Raised when a deployment step fails."""


class UpgradeError(LinestError):
    """Raised when an upgrade cannot be planned or executed."""


class LineraCliError(LinestError):
    """Raised when the underlying linera CLI returns an error."""
