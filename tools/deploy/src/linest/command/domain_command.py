"""Register apps and generate domain.ts from deployment state."""

from __future__ import annotations

from pathlib import Path

from linest.domain_registry import DomainRegistry
from linest.registry import DeploymentRegistry


class DomainCommand:
    """Manage domain-relevant application entries."""

    def __init__(
        self,
        domain_registry: DomainRegistry,
        deployment_registry: DeploymentRegistry,
    ) -> None:
        self.domain_registry = domain_registry
        self.deployment_registry = deployment_registry

    def register(
        self,
        name: str,
        chain_id: str,
        application_id: str,
        wallet_dir: str | None = None,
    ) -> None:
        """Register an application entry for domain generation."""
        self.domain_registry.register(
            name, chain_id, application_id, wallet_dir
        )

    def generate(
        self,
        cluster: str,
        output_path: Path,
    ) -> None:
        """Generate domain.ts from registered and linest-managed apps."""
        entries = self._collect_entries()

        lines: list[str] = []
        lines.append(f"export const SUB_DOMAIN = '{cluster}.'")

        for name, entry in sorted(entries.items()):
            upper = name.upper().replace("-", "_")
            lines.append(
                f"export const {upper}_CHAIN_ID = '{entry['chain_id']}'"
            )
            lines.append(
                f"export const {upper}_APPLICATION_ID = '{entry['application_id']}'"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")

    def _collect_entries(self) -> dict[str, dict[str, str]]:
        """Merge manually registered entries with linest-managed app entries."""
        entries: dict[str, dict[str, str]] = {}

        for name in self.deployment_registry.list_deployments():
            if not name.endswith("-v1"):
                continue
            family_name = name[:-3]
            try:
                family = self.deployment_registry.load_family(family_name)
            except Exception:
                continue
            record = family.versions.get(family.current_version)
            if record is None:
                continue
            try:
                business = self.deployment_registry.load_business_app(record.business_app)
            except Exception:
                continue
            entries[family_name] = {
                "chain_id": business.creator_chain_id,
                "application_id": business.application_id,
            }

        entries.update(self.domain_registry.load())
        return entries
