#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PYPROJECT = ROOT / "pyproject.toml"
SKIVVY_PY = ROOT / "src" / "skivvy" / "skivvy.py"

VERSION_LINE = re.compile(r'(?m)^version\s*=\s*"0\.(\d+)"\s*$')

def read_current() -> int:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = VERSION_LINE.search(text)
    if not m:
        print('Expected: version = "0.<number>" in pyproject.toml', file=sys.stderr)
        sys.exit(1)
    return int(m.group(1))

def write_version(path: Path, new_minor: int) -> None:
    text = path.read_text(encoding="utf-8")
    if not VERSION_LINE.search(text):
        print(f'Expected: version = "0.<number>" in {path}', file=sys.stderr)
        sys.exit(1)
    updated = VERSION_LINE.sub(f'version = "0.{new_minor}"', text, count=1)
    path.write_text(updated, encoding="utf-8")

def main() -> int:
    if not PYPROJECT.exists() or not SKIVVY_PY.exists():
        print("Run from repo root; missing pyproject.toml or skivvy/skivvy.py", file=sys.stderr)
        return 1
    cur = read_current()
    new = cur + 1
    write_version(PYPROJECT, new)
    write_version(SKIVVY_PY, new)
    print(f"Bumped version: 0.{cur} -> 0.{new}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())