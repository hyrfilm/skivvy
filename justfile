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

examples:
	uv run skivvy examples/dummyjson/dummy.json
	uv run skivvy examples/typicode/passing.json

deadcode:
	uv run vulture src/skivvy/ --min-confidence 80 --exclude src/skivvy/config.py

# run via cli
run *args:
	uv run skivvy {{args}}
