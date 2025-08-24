import collections.abc

def subset(d, keys):
    return {k: d[k] for k in keys if k in d}


def map_nested_dicts_py(d, func):
    if isinstance(d, collections.abc.Mapping):
        return {k: map_nested_dicts_py(v, func) for k, v in d.items()}
    else:
        return func(d)
