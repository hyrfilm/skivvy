set shell := ["bash", "-cu"]

default := "test"

test:
	uv run pytest

# Run tests with coverage
cov:
	uv run pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=xml

alias coverage := cov

fmt:
	uv run black src tests

alias format := fmt

ruff:
	uv run ruff check src
	uv run ruff analyze src

alias lint := ruff

# Install dependencies (including dev deps)
sync:
	uv sync --group dev

lock:
	uv lock

# accessing real outbound servers
examples:
	uv run skivvy examples/dummyjson/dummy.json
	uv run skivvy examples/typicode/passing.json

# uses the local loopback server provided used in the sandbox environment
sandbox-examples:
	#!/usr/bin/env bash
	set -euo pipefail
	cd examples/dev_server
	python3 server.py 8080 api &
	sleep 0.5
	printf '%s\n' cfg.json cfg_[^d]*.json | xargs -n1 uv run skivvy

alias sandbox := sandbox-examples

deadcode:
	uv run vulture src/skivvy/ --min-confidence 80 --exclude src/skivvy/config.py

# Generate reference documentation
docs:
	uv run python scripts/generate_docs.py

# run via cli
run *args:
	uv run skivvy {{args}}
