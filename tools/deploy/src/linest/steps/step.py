"""Base class for deployment steps."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.registry import DeploymentRegistry


@dataclass(frozen=True)
class StepResult:
    """Result of executing a deployment step."""

    success: bool
    message: str


class Step(ABC):
    """A single idempotent step in a deployment or upgrade plan."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the step."""

    @abstractmethod
    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        """Execute the step and return the result."""
