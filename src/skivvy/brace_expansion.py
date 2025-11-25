import os

from skivvy.util import str_util, scope, file_util, log

def brace_expand_string(s, **kwargs):
    if not isinstance(s, str):
        return s

    pattern = str_util.compile_regexp(brace_expansion_regexp)
    try:
        s = str_util.expand_string(s, pattern, resolve_funcs=resolvers)
    except ValueError as e:
        log.warning(str(e))
        return s

    auto_coerce_func = kwargs.get("auto_coerce_func", lambda v: v)
    return auto_coerce_func(s)

def variable_resolver(variable_name):
    if scope.has(variable_name):
        return scope.fetch(variable_name)
    return None

def file_resolver(variable_name):
    if os.path.isfile(variable_name):
        return file_util.read_file_contents(variable_name)
    return None

resolvers = [variable_resolver, file_resolver]
brace_expansion_regexp = r'<([^<>]+)>'
