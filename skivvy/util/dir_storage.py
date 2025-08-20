# --- Dir-scoped stash -------------------------------------------------------
import copy

STORE = {}
_CURRENT_DIR_NS = None  # set by runner before executing a test file

def set_dir_namespace(ns: str):
    """Runner MUST call this per test file, e.g., relative directory path."""
    global _CURRENT_DIR_NS
    _CURRENT_DIR_NS = ns

def get_dir_namespace():
    return _CURRENT_DIR_NS

def _require_ns():
    assert _CURRENT_DIR_NS is not None, "INTERNAL BUG: namespace not set for directory"
    return _CURRENT_DIR_NS

def _dir_key(name: str) -> str:
    ns = _require_ns()
    return f"{ns}:{name}"

def is_in_store(name: str) -> bool:
    return _dir_key(name) in STORE

def put_in_storage(name: str, value):
    key = _dir_key(name)
    if key in STORE:
        raise ValueError(f"Variable {key} already exists in store")
    STORE[key] = copy.deepcopy(value)

def get_from_storage(name: str):
    key = _dir_key(name)
    if key not in STORE:
        raise ValueError(f"Variable {key} does not exist in store")
    return copy.deepcopy(STORE.get(_dir_key(name)))
