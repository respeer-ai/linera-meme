"""Application family upgrade history."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from linest.errors import RegistryError, UpgradeError


@dataclass(frozen=True)
class VersionRecord:
    """A single version in an app family's upgrade history."""

    business_app: str
    state_apps: list[str]
    status: str
    handed_off_to: str | None = None
    handed_off_from: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the version record to a dictionary."""
        data: dict[str, Any] = {
            "business_app": self.business_app,
            "state_apps": list(self.state_apps),
            "status": self.status,
        }
        if self.handed_off_to is not None:
            data["handed_off_to"] = self.handed_off_to
        if self.handed_off_from is not None:
            data["handed_off_from"] = self.handed_off_from
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionRecord":
        """Deserialize a version record from a dictionary."""
        return cls(
            business_app=data["business_app"],
            state_apps=list(data.get("state_apps", [])),
            status=data["status"],
            handed_off_to=data.get("handed_off_to"),
            handed_off_from=data.get("handed_off_from"),
        )


@dataclass
class AppFamily:
    """Upgrade history for a business application family."""

    name: str
    env: str
    current_version: int
    versions: dict[int, VersionRecord] = field(default_factory=dict)
    creator_owner: str | None = None
    creator_chain_id: str | None = None
    creator_chain_wallet_dir: str | None = None
    owners: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the app family to a dictionary."""
        data: dict[str, Any] = {
            "name": self.name,
            "env": self.env,
            "current_version": self.current_version,
            "versions": {
                str(version): record.to_dict()
                for version, record in sorted(self.versions.items())
            },
        }
        if self.creator_owner is not None:
            data["creator_owner"] = self.creator_owner
        if self.creator_chain_id is not None:
            data["creator_chain_id"] = self.creator_chain_id
        if self.creator_chain_wallet_dir is not None:
            data["creator_chain_wallet_dir"] = self.creator_chain_wallet_dir
        if self.owners:
            data["owners"] = list(self.owners)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppFamily":
        """Deserialize an app family from a dictionary."""
        versions = {
            int(version): VersionRecord.from_dict(record)
            for version, record in data.get("versions", {}).items()
        }
        return cls(
            name=data["name"],
            env=data["env"],
            current_version=data["current_version"],
            versions=versions,
            creator_owner=data.get("creator_owner"),
            creator_chain_id=data.get("creator_chain_id"),
            creator_chain_wallet_dir=data.get("creator_chain_wallet_dir"),
            owners=list(data.get("owners", [])),
        )

    @classmethod
    def create(cls, name: str, env: str) -> "AppFamily":
        """Create a new empty app family."""
        return cls(
            name=name,
            env=env,
            current_version=0,
            versions={},
            owners=[],
        )

    def add_version(
        self,
        version: int,
        business_app: str,
        state_apps: list[str],
        status: str = "planned",
    ) -> None:
        """Add a new version record to the family."""
        if version in self.versions:
            raise RegistryError(f"Version {version} already exists in {self.name}")
        self.versions[version] = VersionRecord(
            business_app=business_app,
            state_apps=list(state_apps),
            status=status,
        )

    def get_version(self, version: int) -> VersionRecord:
        """Return the version record for the given version."""
        if version not in self.versions:
            raise RegistryError(f"Version {version} not found in {self.name}")
        return self.versions[version]

    def previous_version(self, version: int) -> int | None:
        """Return the version immediately before the given version."""
        previous_versions = [v for v in self.versions if v < version]
        if not previous_versions:
            return None
        return max(previous_versions)

    def validate_upgrade_target(self, version: int) -> None:
        """Validate that the given version is a valid upgrade target."""
        if version <= 0:
            raise UpgradeError("Version must be positive")

        if self.current_version == 0:
            return

        if version <= self.current_version:
            raise UpgradeError(
                f"Version must be greater than current: current={self.current_version}, target={version}"
            )
