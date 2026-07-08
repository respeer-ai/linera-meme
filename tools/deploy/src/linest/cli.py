"""Command-line interface for linest."""

import argparse
import sys
from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.command.deploy_command import DeployCommand
from linest.config import NetworkConfig
from linest.errors import LinestError
from linest.registry import DeploymentRegistry


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linest",
        description="Deployment and upgrade tool for Linera typed-state applications.",
    )
    parser.add_argument(
        "--env",
        default="local",
        help="Deployment environment (default: local)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        help="Base directory for linest configuration and registry",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    app_parser = subparsers.add_parser("app", help="Manage business applications")
    app_subparsers = app_parser.add_subparsers(dest="app_command", required=True)

    deploy_parser = app_subparsers.add_parser("deploy", help="Deploy or upgrade an app")
    deploy_parser.add_argument("--name", required=True, help="Application family name")
    deploy_parser.add_argument("--version", type=int, required=True, help="Target version")
    deploy_parser.add_argument(
        "--contract-bytecode",
        help="Path to business app contract bytecode",
    )
    deploy_parser.add_argument(
        "--service-bytecode",
        help="Path to business app service bytecode",
    )
    deploy_parser.add_argument(
        "--state-contract-bytecode",
        help="Path to state app contract bytecode",
    )
    deploy_parser.add_argument(
        "--state-service-bytecode",
        help="Path to state app service bytecode",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without executing",
    )

    status_parser = app_subparsers.add_parser("status", help="Show app deployment status")
    status_parser.add_argument("--name", required=True, help="Application family name")

    return parser


def _handle_status(args: argparse.Namespace) -> int:
    config = NetworkConfig.load(args.env, base_dir=args.base_dir)
    registry = DeploymentRegistry(config.deployments_dir(args.base_dir))
    family = registry.load_family(args.name)

    print(f"{family.name} ({family.env})")
    print(f"  current version: {family.current_version}")
    for version, record in sorted(family.versions.items()):
        print(f"  v{version}: {record.business_app} [{record.status}]")
        for state_app in record.state_apps:
            print(f"    state app: {state_app}")
        if record.handed_off_to:
            print(f"    handed off to: v{record.handed_off_to}")
        if record.handed_off_from:
            print(f"    handed off from: v{record.handed_off_from}")
    return 0


def _handle_deploy(args: argparse.Namespace) -> int:
    config = NetworkConfig.load(args.env, base_dir=args.base_dir)
    registry = DeploymentRegistry(config.deployments_dir(args.base_dir))
    linera_client = LineraClient(
        config.wallet_dir, args.name, wallet_services=config.wallet_services
    )
    query_client = QueryClient(config.query_service_url)

    command = DeployCommand(
        config=config,
        registry=registry,
        linera_client=linera_client,
        query_client=query_client,
    )

    command.deploy(
        name=args.name,
        version=args.version,
        contract_bytecode=args.contract_bytecode,
        service_bytecode=args.service_bytecode,
        state_contract_bytecode=args.state_contract_bytecode,
        state_service_bytecode=args.state_service_bytecode,
        dry_run=args.dry_run,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the linest CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "app":
            if args.app_command == "deploy":
                return _handle_deploy(args)
            if args.app_command == "status":
                return _handle_status(args)
    except LinestError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Unknown command: {args.command} {getattr(args, 'app_command', '')}")
    return 1
