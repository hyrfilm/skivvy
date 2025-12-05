import collections.abc
from functools import wraps
from operator import itemgetter


def subset(d: dict, keys: list[str], include_none=True) -> dict:
    """Returns a subset of a dictionary whose keys are included in keys."""

    def should_include(key):
        if include_none:
            return key in d
        else:
            return d.get(key, None) is not None

    return {k: d[k] for k in keys if should_include(k)}


def remap_keys(d: dict, remap: dict[str, str]) -> dict:
    """Returns a dictionary where keys are renamed according to remap (e.g. {'old: 'new'}).
    Other keys are left alone and returned in the new dictionary."""
    return {remap.get(k, k): v for k, v in d.items()}


def map_nested_dicts_py(d, func):
    if isinstance(d, collections.abc.Mapping):
        return {k: map_nested_dicts_py(v, func) for k, v in d.items()}
    else:
        return func(d)


def wrap_in_tuple(fn):
    @wraps(fn)
    def _inner(d, *keys):
        if len(keys) == 0:
            return ()
        items = fn(d, *keys)
        return items if isinstance(items, tuple) else (items,)

    return _inner


@wrap_in_tuple
def get_all(d, *keys):
    """
    retrieves all keys from a dict or raises an error
    """
    _get = itemgetter(*keys)
    return _get(d)


@wrap_in_tuple
def get_many(d, *keys):
    """
    returns as many keys as it finds from a dict
    """
    return filter_null_from_list([d.get(key) for key in keys])


def filter_null_from_list(l):
    """
    removes all values from a list that are None
    """
    return filter(lambda x: x is not None, l)


def filter_null_from_dict(d):
    """
    removes all values from a dict that are None
    """
    return {k: v for k, v in d.items() if v is not None}
