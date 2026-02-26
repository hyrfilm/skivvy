set shell := ["bash", "-cu"]

default := "test"

test:
	uv run pytest

# Run tests with coverage
cov:
	uv run pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=xml

alias coverage := cov

# format code
fmt:
	uv run black src tests

# Install dependencies (including dev deps)
sync:
	uv sync --group dev

lock:
	uv lock

examples:
	uv run skivvy examples/dummyjson/dummy.json
	uv run skivvy examples/typicode/passing.json

# run via cli
run *args:
	uv run skivvy {{args}}
