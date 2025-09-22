from skivvy.matchers import brace_expand
from skivvy.util import dict_util


def expand(obj:str | dict, auto_coerce) -> str | dict:
    if isinstance(obj, str):
        return brace_expand(obj, auto_coerce)
    elif isinstance(obj, dict):
        return dict_util.map_nested_dicts_py(obj, brace_expand)
    else:
        return obj
