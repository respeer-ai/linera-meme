"""Command-line interface for linest."""

import argparse
import json
import sys
from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.command.bootstrap_command import BootstrapCommand
from linest.command.deploy_command import DeployCommand
from linest.command.domain_command import DomainCommand
from linest.command.fund_command import FundCommand
from linest.config import NetworkConfig
from linest.domain_registry import DomainRegistry
from linest.errors import LinestError
from linest.registry import DeploymentRegistry
from linest.version import read_crate_version


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

    bootstrap_parser = subparsers.add_parser(
        "bootstrap", help="Create shared wallets and start services"
    )
    bootstrap_parser.add_argument(
        "--faucet-url",
        dest="faucet_url",
        required=True,
        help="Faucet URL for wallet creation",
    )
    bootstrap_parser.add_argument(
        "--wallet-dir",
        dest="wallet_dir",
        required=True,
        help="Root directory for all wallets",
    )
    bootstrap_parser.add_argument(
        "--operator-wallet-dir",
        dest="operator_wallet_dir",
        required=True,
        help="Directory for the operator wallet",
    )
    bootstrap_parser.add_argument(
        "--query-wallet-dir",
        dest="query_wallet_dir",
        required=True,
        help="Directory for the query service wallet",
    )
    bootstrap_parser.add_argument(
        "--query-service-port",
        dest="query_service_port",
        type=int,
        default=24080,
        help="Port for the query service (default: 24080)",
    )

    app_parser = subparsers.add_parser("app", help="Manage business applications")
    app_subparsers = app_parser.add_subparsers(dest="app_command", required=True)

    deploy_parser = app_subparsers.add_parser("deploy", help="Deploy or upgrade an app")
    deploy_parser.add_argument("--name", required=True, help="Application family name")
    deploy_parser.add_argument(
        "--version",
        type=int,
        help="Target version (defaults to the app crate version from --repo-dir)",
    )
    deploy_parser.add_argument(
        "--creator-chain-id",
        dest="creator_chain_id",
        help="Chain ID on which applications are created (defaults to registry)",
    )
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
        "--operation-type",
        dest="operation_type",
        help="BCS operation type for app-chain mutations (default: derived from family name)",
    )
    deploy_parser.add_argument(
        "--no-business-argument",
        dest="no_business_argument",
        action="store_true",
        help="Do not pass --json-argument when creating the business app",
    )
    deploy_parser.add_argument(
        "--repo-dir",
        dest="repo_dir",
        type=Path,
        default=Path.cwd(),
        help="Code repository root used to locate ABI source files by convention (default: current directory)",
    )
    deploy_parser.add_argument(
        "--ensure-wallet",
        dest="ensure_wallet",
        action="store_true",
        help="Create the app family wallets and chain if they do not exist",
    )
    deploy_parser.add_argument(
        "--faucet-url",
        dest="faucet_url",
        help="Faucet URL used when --ensure-wallet creates wallets",
    )
    deploy_parser.add_argument(
        "--wallet-owner-count",
        dest="wallet_owner_count",
        type=int,
        default=1,
        help="Number of owner wallets to create besides the creator wallet (default: 1)",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without executing",
    )

    status_parser = app_subparsers.add_parser("status", help="Show app deployment status")
    status_parser.add_argument("--name", required=True, help="Application family name")
    status_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    domain_parser = subparsers.add_parser("domain", help="Manage domain entries")
    domain_subparsers = domain_parser.add_subparsers(
        dest="domain_command", required=True
    )

    register_parser = domain_subparsers.add_parser(
        "register", help="Register an app chain/application id"
    )
    register_parser.add_argument("--name", required=True, help="Application name")
    register_parser.add_argument("--chain-id", required=True, help="Chain ID")
    register_parser.add_argument(
        "--application-id", required=True, help="Application ID"
    )

    generate_parser = domain_subparsers.add_parser(
        "generate", help="Generate domain.ts"
    )
    generate_parser.add_argument(
        "--cluster", required=True, help="Cluster name used for SUB_DOMAIN"
    )
    generate_parser.add_argument(
        "--output", type=Path, required=True, help="Output path for domain.ts"
    )

    fund_parser = subparsers.add_parser("fund", help="Fund chains")
    fund_subparsers = fund_parser.add_subparsers(
        dest="fund_command", required=True
    )

    fund_chains_parser = fund_subparsers.add_parser(
        "chains", help="Top up chain balances from a source wallet or faucet"
    )
    fund_chains_parser.add_argument(
        "--min-balance",
        dest="min_balance",
        type=float,
        default=100.0,
        help="Minimum target balance (default: 100)",
    )
    fund_chains_parser.add_argument(
        "--source-wallet-dir",
        dest="source_wallet_dir",
        type=Path,
        help="Existing wallet directory to use as the funding source",
    )
    fund_chains_parser.add_argument(
        "--claim-from-faucet",
        dest="claim_from_faucet",
        action="store_true",
        help="Claim a chain from the faucet to use as the funding source",
    )
    fund_chains_parser.add_argument(
        "--faucet-url",
        dest="faucet_url",
        help="Faucet URL used when --claim-from-faucet is set",
    )

    fund_subparsers.add_parser(
        "funder-list", help="List claimed funder chains and their balances"
    )

    fund_subparsers.add_parser(
        "funder-clean", help="Remove spent funder wallets"
    )

    return parser


def _handle_bootstrap(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    config = NetworkConfig(
        env=args.env,
        operator="",
        query_service_url="",
        wallet_dir=args.wallet_dir,
        wallet_services={},
    )
    linera_client = LineraClient(
        wallet_dir=args.wallet_dir,
        app_name="bootstrap",
    )

    command = BootstrapCommand(
        config=config,
        linera_client=linera_client,
        base_dir=base_dir,
        env=args.env,
    )
    command.bootstrap(
        faucet_url=args.faucet_url,
        operator_wallet_dir=Path(args.operator_wallet_dir),
        query_wallet_dir=Path(args.query_wallet_dir),
        query_service_port=args.query_service_port,
    )
    command.keep_alive()
    return 0


def _handle_domain_register(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    domain_registry = DomainRegistry(base_dir / "domain.json")
    command = DomainCommand(
        domain_registry=domain_registry,
        deployment_registry=DeploymentRegistry(base_dir / "deployments" / args.env),
    )
    command.register(
        name=args.name,
        chain_id=args.chain_id,
        application_id=args.application_id,
    )
    return 0


def _handle_domain_generate(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    domain_registry = DomainRegistry(base_dir / "domain.json")
    command = DomainCommand(
        domain_registry=domain_registry,
        deployment_registry=DeploymentRegistry(base_dir / "deployments" / args.env),
    )
    command.generate(
        cluster=args.cluster,
        output_path=args.output,
    )
    return 0


def _handle_status(args: argparse.Namespace) -> int:
    config = NetworkConfig.load(args.env, base_dir=args.base_dir)
    registry = DeploymentRegistry(config.deployments_dir(args.base_dir))
    family = registry.load_family(args.name)

    if args.format == "json":
        current_version = family.current_version
        record = family.versions.get(current_version)
        output: dict = {
            "name": family.name,
            "env": family.env,
            "current_version": current_version,
        }
        if record is not None:
            business_app = registry.load_business_app(record.business_app)
            output["business_app"] = {
                "name": business_app.name,
                "application_id": business_app.application_id,
                "creator_chain_id": business_app.creator_chain_id,
            }
            output["state_apps"] = []
            for state_app_name in record.state_apps:
                state_app = registry.load_state_app(state_app_name)
                output["state_apps"].append(
                    {
                        "name": state_app.name,
                        "application_id": state_app.application_id,
                        "creator_chain_id": state_app.creator_chain_id,
                    }
                )
            output["status"] = record.status
            output["handed_off_to"] = record.handed_off_to
            output["handed_off_from"] = record.handed_off_from
        print(json.dumps(output, indent=2))
        return 0

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
    version = args.version
    if version is None:
        version = read_crate_version(args.repo_dir, args.name)

    config = NetworkConfig.load(args.env, base_dir=args.base_dir)
    registry = DeploymentRegistry(config.deployments_dir(args.base_dir))
    # App-chain mutations (appendState, handoff) are signed directly by the
    # creator wallet via `linera execute-application-operation`, so no wallet
    # service is required.
    linera_client = LineraClient(
        wallet_dir=config.wallet_dir,
        app_name=args.name,
        repo_dir=args.repo_dir,
    )
    query_client = QueryClient(config.query_service_url)

    command = DeployCommand(
        config=config,
        registry=registry,
        linera_client=linera_client,
        query_client=query_client,
        base_dir=args.base_dir,
    )

    result = command.deploy(
        name=args.name,
        version=version,
        contract_bytecode=args.contract_bytecode,
        service_bytecode=args.service_bytecode,
        state_contract_bytecode=args.state_contract_bytecode,
        state_service_bytecode=args.state_service_bytecode,
        repo_dir=args.repo_dir,
        creator_chain_id=args.creator_chain_id,
        dry_run=args.dry_run,
        ensure_wallet=args.ensure_wallet,
        faucet_url=args.faucet_url,
        wallet_owner_count=args.wallet_owner_count,
        operation_type=args.operation_type,
        no_business_argument=args.no_business_argument,
    )
    return 0 if result.status in ("skipped", "deployed") else 1


def _handle_fund_chains(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    config = NetworkConfig.load(args.env, base_dir=base_dir)
    registry = DeploymentRegistry(config.deployments_dir(base_dir))
    linera_client = LineraClient(
        wallet_dir=config.wallet_dir,
        app_name="fund",
    )

    source_wallet_dir = args.source_wallet_dir
    faucet_url = args.faucet_url
    if args.claim_from_faucet:
        faucet_url = args.faucet_url
        source_wallet_dir = None

    command = FundCommand(
        config=config,
        registry=registry,
        linera_client=linera_client,
        base_dir=base_dir,
    )
    command.fund_chains(
        min_balance=args.min_balance,
        source_wallet_dir=source_wallet_dir,
        faucet_url=faucet_url,
    )
    return 0


def _handle_funder_list(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    config = NetworkConfig.load(args.env, base_dir=base_dir)
    linera_client = LineraClient(
        wallet_dir=config.wallet_dir,
        app_name="fund",
    )
    command = FundCommand(
        config=config,
        registry=DeploymentRegistry(config.deployments_dir(base_dir)),
        linera_client=linera_client,
        base_dir=base_dir,
    )
    for funder in command.list_funders():
        print(f"{funder['chain_id']}  {funder['balance']}  {funder['wallet_dir']}")
    return 0


def _handle_funder_clean(args: argparse.Namespace) -> int:
    base_dir = args.base_dir or NetworkConfig.default_base_dir()
    config = NetworkConfig.load(args.env, base_dir=base_dir)
    linera_client = LineraClient(
        wallet_dir=config.wallet_dir,
        app_name="fund",
    )
    command = FundCommand(
        config=config,
        registry=DeploymentRegistry(config.deployments_dir(base_dir)),
        linera_client=linera_client,
        base_dir=base_dir,
    )
    removed = command.clean_funders()
    print(f"Removed {removed} spent funder wallet(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the linest CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "bootstrap":
            return _handle_bootstrap(args)
        if args.command == "app":
            if args.app_command == "deploy":
                return _handle_deploy(args)
            if args.app_command == "status":
                return _handle_status(args)
        if args.command == "domain":
            if args.domain_command == "register":
                return _handle_domain_register(args)
            if args.domain_command == "generate":
                return _handle_domain_generate(args)
        if args.command == "fund":
            if args.fund_command == "chains":
                return _handle_fund_chains(args)
            if args.fund_command == "funder-list":
                return _handle_funder_list(args)
            if args.fund_command == "funder-clean":
                return _handle_funder_clean(args)
    except LinestError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(f"Unknown command: {args.command} {getattr(args, 'app_command', '')}")
    return 1
