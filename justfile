set shell := ["bash", "-cu"]

default := "test"

test:
	uv run pytest

# Run tests with coverage
cov:
	uv run pytest --cov=src --cov-report=term-missing

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

# Prototype: compare different diff renderings for each failing testcase
diff-examples *args:
	uv run python scripts/compare_failure_diffs.py {{args}}

# Prototype: compact-first diff comparison for huge failures (projected diffs first)
diff-examples-compact *args:
	uv run python scripts/compare_failure_diffs.py --compact-mode {{args}}
