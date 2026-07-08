# linest

Deployment and upgrade tool for Linera typed-state applications.

## Install

```bash
cd tools/deploy
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
linest app deploy --name ams --version 1 --env local --state-bytecode PATH
linest app deploy --name ams --version 2 --env local
linest app status --name ams --env local
```

Deploy commands retry transient `linera` CLI errors such as
`A different block was already committed`.

Future command (not yet implemented):

```bash
linest bootstrap --env local
```

## Configuration

Network configuration lives in `~/.config/micromeme/networks/<env>/config.json`.

Deployment registry lives in `~/.config/micromeme/deployments/<env>/`.
