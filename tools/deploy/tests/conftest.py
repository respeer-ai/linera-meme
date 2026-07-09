"""Shared test configuration."""

from __future__ import annotations

import pytest

from linest.client.chain_manager import MultiOwnerChainManager
from linest.command.fund_command import FundCommand


@pytest.fixture(autouse=True)
def short_funding_cooldown(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep funding cooldown loops fast in unit tests."""
    monkeypatch.setattr(
        FundCommand, "_FUNDING_COOLDOWN_SECONDS", 0.01
    )
    monkeypatch.setattr(
        FundCommand, "_FUNDING_COOLDOWN_INTERVAL", 0.001
    )
    monkeypatch.setattr(
        MultiOwnerChainManager, "_FUNDING_COOLDOWN_SECONDS", 0.01
    )
    monkeypatch.setattr(
        MultiOwnerChainManager, "_FUNDING_COOLDOWN_INTERVAL", 0.001
    )
