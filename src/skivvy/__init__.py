from importlib import metadata as _metadata
from pathlib import Path
import tomllib


def _load_version() -> str:
    """Return the package version, preferring installed metadata."""
    try:
        return _metadata.version("skivvy")
    except _metadata.PackageNotFoundError:
        project_root = Path(__file__).resolve().parent.parent
        pyproject = project_root / "pyproject.toml"
        if pyproject.is_file():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                return data.get("project", {}).get("version", "0.0.0")
            except Exception:
                pass
        return "0.0.0"


__version__ = _load_version()
