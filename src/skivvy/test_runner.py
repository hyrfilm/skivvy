import json
from functools import partial
from typing import Dict, Mapping, Callable
from urllib.parse import urljoin

from skivvy.brace_expansion import brace_expand_string
from skivvy.skivvy_config2 import Settings, conf_get
from skivvy.util import dict_util, log, str_util
from skivvy.util.dict_util import get_all, subset

def create_request(test_config:Dict[str, object]) -> tuple[dict, dict]:
    """
    Creates and validates a request given a test_config dict.
    The return value of this function can just be sent as-is to
    """
    # TODO: Before we reach here we should have just already have this dict filled with
    # TODO: the necessary values by just iterating over the dict and for each option either it would have a default or we would raise a validation exception
    required_fields = (Settings.BASE_URL.key, Settings.URL.key, Settings.METHOD.key)
    base_url, url, method = dict_util.get_all(test_config, *required_fields)
    url = urljoin(base_url, url)
    test_config[Settings.URL.key] = url
    log.debug(f'Creating request {method}: {url}')

    # apply for these fields, the ones not present will just be ignored
    options = (Settings.URL, Settings.BODY, Settings.READ_HEADERS, Settings.WRITE_HEADERS)
    fields_to_expand = [opt.key for opt in options]

    # in either case, we get back a dict that represents all configuration related to the request
    request_config = brace_expand_fields(test_config, *fields_to_expand)
    # validate and warn if the request looks odd
    is_valid = validate_request_body(request_config)
    if not is_valid:
        log.warning(f"Request does not seem valid: {method, url}")

    request_fields = [Settings.METHOD, Settings.URL, Settings.QUERY, Settings.BODY, Settings.FORM, Settings.UPLOAD]
    request_data = subset(request_config, [option.key for option in request_fields], include_none=False)

    return request_data, request_config

def validate_request_body(d):
    """Validates that the body data makes sense for the HTTP method"""
    url, method = get_all(d, Settings.URL.key, Settings.METHOD.key)

    json_data = conf_get(d, Settings.BODY)
    form_data = conf_get(d, Settings.FORM)
    upload = conf_get(d, Settings.UPLOAD)

    # TODO: stop lowering everywhere
    match method.lower():
        case "post" | "put" | "patch" | "delete":
            # These methods can have body data - validate no conflicts
            body_fields = [json_data, form_data, upload]
            match body_fields:
                case [None, None, None]:
                    log.debug(f'No data provided for {method} {url}')
                case [json_data, None, None]:
                    log.debug(f'{method} {url} (JSON payload)')
                case [None, form_data, None]:
                    log.debug(f'{method} {url} (multi-form payload)')
                case [None, None, upload]:
                    log.debug(f'{method} {url} (file upload)')
                case _:
                    log.warning(f"Multiple body data for {method} {url}")
                    log.warning(f"json: {json_data} form: {form_data} upload: {upload}")
                    return False
        case "get" | "delete" | "head" | "options":
            # These methods shouldn't have body data
            if any([json_data, form_data, upload]):
                log.warning(f"Multiple body data for {method} {url} - this may cause issues")
                return False
        case _:
            raise ValueError(f"Unsupported HTTP method: {method}")
    return True

def brace_expand_fields(request_dict: Mapping[str,object], *keys: str) -> Dict[str, object]:
    """
    Takes a list of keys and applies brace expansion for each key it finds, others are silently ignored.
    Returns a new dict, all the other entries as well.
    If is_enabled is False, then it will simply just return a new dict without any expansion applied.
    """
    expand_func = get_brace_expansion_func(request_dict)
    result = json.loads(json.dumps(dict(request_dict)))

    for k in keys:
        field = result.get(k)
        if field:
            field = dict_util.map_nested_dicts_py(field, expand_func)
            result[k] = field
    return result

def get_brace_expansion_func(config: Mapping[str,object]) -> Callable:
    if conf_get(config, Settings.AUTO_COERCE):
        auto_coerce_func = auto_coercer
    else:
        auto_coerce_func = auto_coercer_noop

    if conf_get(config, Settings.BRACE_EXPANSION):
        brace_expand_func = partial(brace_expand_string, auto_coerce_func=auto_coerce_func)
    else:
        brace_expand_func = brace_expander_noop

    return brace_expand_func

def auto_coercer(s):
    return str_util.coerce_str_to_int(s)

# identity function, when auto coercion is not enabled
def auto_coercer_noop(s):
    return s

def brace_expander(s, **kwargs):
    return brace_expand_string(s, **kwargs)

# identity function, when brace expansion is not enabled
def brace_expander_noop(s, **_kwargs):
    return s
