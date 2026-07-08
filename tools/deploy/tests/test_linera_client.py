"""Tests for LineraClient."""

from unittest.mock import MagicMock, patch

import pytest

from linest.client.linera_client import LineraClient
from linest.errors import ConfigError, LineraCliError


@pytest.fixture
def client() -> LineraClient:
    return LineraClient(
        "/wallets",
        "ams",
        wallet_services={"ams": "http://ams-wallet:8080"},
    )


def _completed_process(stdout: str = "", stderr: str = "", returncode: int = 0) -> MagicMock:
    process = MagicMock()
    process.returncode = returncode
    process.stdout = stdout
    process.stderr = stderr
    return process


def test_default_chain_id_returns_default_tag(client: LineraClient) -> None:
    stdout = """
Chain ID:             admin-chain
Tags:                 ADMIN
-----------------------
Chain ID:             default-chain
Tags:                 DEFAULT
"""
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process(stdout)

        chain_id = client.default_chain_id()

        assert chain_id == "default-chain"
        args = mock_run.call_args[0][0]
        assert "wallet" in args
        assert "0/wallet.json" in args[args.index("--wallet") + 1]


def test_default_chain_id_raises_when_no_default_tag(client: LineraClient) -> None:
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process("Chain ID: chain1\nTags: ADMIN\n")

        with pytest.raises(LineraCliError, match="no DEFAULT chain"):
            client.default_chain_id()


def test_publish_module_uses_publisher_wallet(client: LineraClient) -> None:
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process("module-id-123\n")

        module_id = client.publish_module("contract.wasm", "service.wasm")

        assert module_id == "module-id-123"
        args = mock_run.call_args[0][0]
        assert "publish-module" in args
        wallet_path = args[args.index("--wallet") + 1]
        assert "creator/wallet.json" in wallet_path


def test_create_application_uses_creator_wallet(client: LineraClient) -> None:
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process("app-id-456\n")

        app_id = client.create_application(
            "module-id-123", "chain1", argument={"key": "value"}
        )

        assert app_id == "app-id-456"
        args = mock_run.call_args[0][0]
        assert "create-application" in args
        wallet_path = args[args.index("--wallet") + 1]
        assert "0/wallet.json" in wallet_path
        assert "--json-argument" in args


def test_create_application_without_argument_or_parameters(client: LineraClient) -> None:
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process("app-id-789\n")

        app_id = client.create_application("module-id-123", "chain1")

        assert app_id == "app-id-789"
        args = mock_run.call_args[0][0]
        assert "--json-argument" not in args
        assert "--json-parameters" not in args


def test_linera_command_failure_raises(client: LineraClient) -> None:
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        mock_run.return_value = _completed_process(
            stderr="some error", returncode=1
        )

        with pytest.raises(LineraCliError, match="linera command failed"):
            client.publish_module("contract.wasm", "service.wasm")


def test_publish_module_retries_on_block_conflict(client: LineraClient) -> None:
    conflict = _completed_process(
        stderr="A different block was already committed", returncode=1
    )
    success = _completed_process("module-id-123\n")
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        with patch.object(client.retry_policy, "_sleep"):
            mock_run.side_effect = [conflict, success]

            module_id = client.publish_module("contract.wasm", "service.wasm")

        assert module_id == "module-id-123"
        assert mock_run.call_count == 2


def test_publish_module_does_not_retry_fatal_error(client: LineraClient) -> None:
    fatal = _completed_process(stderr="Invalid bytecode format", returncode=1)
    with patch("linest.client.linera_client.subprocess.run") as mock_run:
        with patch.object(client.retry_policy, "_sleep"):
            mock_run.return_value = fatal

            with pytest.raises(LineraCliError, match="Invalid bytecode format"):
                client.publish_module("contract.wasm", "service.wasm")

        assert mock_run.call_count == 1


def test_extract_id_from_multiline_output(client: LineraClient) -> None:
    assert client._extract_id("\n\n  final-id  \n") == "final-id"


def test_extract_id_raises_on_empty_output(client: LineraClient) -> None:
    with pytest.raises(LineraCliError, match="empty output"):
        client._extract_id("")


def test_wallet_url_for_known_app(client: LineraClient) -> None:
    assert client.wallet_url_for("ams") == "http://ams-wallet:8080"


def test_wallet_url_for_unknown_app_raises(client: LineraClient) -> None:
    with pytest.raises(ConfigError, match="No wallet service URL"):
        client.wallet_url_for("unknown")
