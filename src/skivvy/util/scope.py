import os
import string
from collections import defaultdict
from typing import KeysView

_store : dict[str, dict] = defaultdict(lambda: {})
_allowed_key_chars = set(string.ascii_lowercase + string.digits + '_-.,/\\')

def get_current_namespace():
    return os.environ.get('SKIVVY_CURRENT_DIR', os.getcwd())

def get_all_namespaces() -> KeysView[str]:
    return _store.keys()

def _get_scope_storage(namespace) -> dict | None:
    assert isinstance(namespace, str) == True;
    return _store[namespace]

def _get_current_scope_storage() -> dict:
    ns = get_current_namespace()
    scope = _get_scope_storage(ns)
    assert scope is not None
    return scope

def dump(namespace):
    scope = _get_scope_storage(namespace)
    if scope is None:
        return None
    return {k: v for k, v in scope.items()}

# Probably overkill but consider checking whether what we store is a primitive or not
# we could just turn that into json if we would think there was any realistic possibility of mutation happening

def _get(name):
    return _get_current_scope_storage().get(name)

def _put(name, value):
    _get_current_scope_storage()[name] = value

def do_variable_validation(name):
    msg = f"""Received the variable name: '{name}' - note that variable names needs to be strings, start with an alphabetic char, and are are case-insensitive.
    Full list of allowed chars: {_allowed_key_chars}   
    """
    if not isinstance(name, str):
        return False, msg

    match list(name):
        case [head, *tail]:
            if not head.isalpha():
                return False, msg
            for c in tail:
                if not c in _allowed_key_chars: return False, msg
            return True, msg

        case _:
            return False, msg

def as_key(name):
    name = name.lower()
    valid, msg = do_variable_validation(name)
    if not valid:
        # is this really the most fitting exception? seems like we over-use it...
        raise ValueError(msg)
    return name

def has(name: str, normalize=True) -> bool:
    if normalize:
        name = as_key(name)
    scope = _get_current_scope_storage()
    return name in scope

def store(key: str, value):
    key = as_key(key)
    if has(key, normalize=False):
        raise ValueError(f"Variable {key} already declared")
    return _put(key, value)

def fetch(key: str):
    key = as_key(key)
    if not has(key, normalize=False):
        raise ValueError(f"Variable {key} is undeclared")
    return _get(key)

def dump_all():
    result = {}
    for ns in get_all_namespaces():
        result[ns] = dump(ns)

def current():
    return dump(get_current_namespace())