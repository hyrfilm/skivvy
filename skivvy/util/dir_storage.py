# --- Dir-scoped stash -------------------------------------------------------
import copy
import os

STORE = {}

def get_dir_namespace():
    return os.environ["SKIVVY_CURRENT_DIR"]

def _require_ns():
    assert get_dir_namespace() is not None, "INTERNAL BUG: namespace not set for directory"
    return get_dir_namespace()

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
