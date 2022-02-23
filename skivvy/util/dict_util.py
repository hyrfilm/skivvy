def subset(d, keys):
    return {k: d[k] for k in keys if k in d}


def map_nested_dicts_py(d, func):
    return map_nested_dicts_py2(d, func)


def map_nested_dicts_py2(d, func):
    import collections

    if isinstance(d, collections.Mapping):
        return {k: map_nested_dicts_py2(v, func) for k, v in d.iteritems()}
    else:
        return func(d)

# python3 version
# def map_nested_dicts_py3(ob, func):
#     import collections.abc
#
#     if isinstance(ob, collections.abc.Mapping):
#         return {k: map_nested_dicts_py3(v, func) for k, v in ob.items()}
#     else:
#         return func(ob)
