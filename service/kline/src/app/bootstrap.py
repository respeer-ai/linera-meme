from dataclasses import dataclass

from app.config import KlineAppConfig


@dataclass(slots=True)
class AppContainer:
    config: KlineAppConfig
    services: dict[str, object]


def build_container(config: KlineAppConfig) -> AppContainer:
    """Create a minimal service container for phase-1 migration work."""
    return AppContainer(config=config, services={})

