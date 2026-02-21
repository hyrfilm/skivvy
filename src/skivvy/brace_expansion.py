import os

from skivvy.util import str_util, scope, file_util, log


def is_env_variable_name(variable_name: str) -> bool:
    return variable_name.lower().startswith("env.")


def brace_expand_string(s, **kwargs):
    if not isinstance(s, str):
        return s

    warn = kwargs.get("warn", True)
    strict = kwargs.get("strict", False)

    pattern = str_util.compile_regexp(brace_expansion_regexp)
    try:
        s = str_util.expand_string(s, pattern, resolve_funcs=resolvers)
    except ValueError as e:
        if warn:
            log.warning(f"[yellow]Brace expansion warning:[/yellow] {e}")
        if strict:
            raise
        return s

    auto_coerce_func = kwargs.get("auto_coerce_func", lambda v: v)
    return auto_coerce_func(s)


def variable_resolver(variable_name):
    if is_env_variable_name(variable_name):
        return None
    if scope.has(variable_name):
        return scope.fetch(variable_name)
    return None


def env_resolver(variable_name):
    prefix = "env."
    if not is_env_variable_name(variable_name):
        return None

    env_name = variable_name[len(prefix):]
    if env_name == "":
        return None
    return os.environ.get(env_name)


def file_resolver(variable_name):
    if is_env_variable_name(variable_name):
        return None
    if os.path.isfile(variable_name):
        return file_util.read_file_contents(variable_name)
    return None


resolvers = [env_resolver, variable_resolver, file_resolver]
brace_expansion_regexp = r"<([^<>]+)>"
