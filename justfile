set shell := ["bash", "-cu"]

default := "test"

test:
	uv run pytest

# Run tests with coverage
cov:
	uv run pytest --cov=src --cov-report=term-missing

# Install dependencies (including dev deps)
sync:
	uv sync --group dev

lock:
	uv lock

# run via cli
run *args:
	uv run skivvy {{args}}
