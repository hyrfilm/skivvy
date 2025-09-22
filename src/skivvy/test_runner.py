import json
from typing import Dict, Mapping
from urllib.parse import urljoin

from skivvy.brace_expansion import expand
from skivvy.skivvy_config2 import Settings, conf_get
from skivvy.util import dict_util, log
from skivvy.util.dict_util import filter_null_from_dict, get_all, get_many


def create_request(test_config:Dict[str, object]) -> Dict[str, object]:
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
    # finally, filter out null / none fields
    request_config = filter_null_from_dict(request_config)
    # validate and warn if the request looks odd
    is_valid = validate_request_body(request_config)
    if not is_valid:
        log.warning(f"Request does not seem valid: {method, url}")

    return request_config

def validate_request_body(d):
    """Validates that the body data makes sense for the HTTP method"""
    url, method = get_all(d, Settings.URL.key, Settings.METHOD.key)

    json_data = conf_get(d, Settings.BODY)
    form_data = conf_get(d, Settings.FORM)
    upload = conf_get(d, Settings.UPLOAD)

    # TODO: stop lowering everywhere
    match method.lower():
        case "post" | "put" | "patch":
            # These methods can have body data - validate no conflicts
            body_fields = [json_data, form_data, upload]
            match body_fields:
                case [json_data, None, None]:
                    log.debug(f'{method} {url} (JSON payload)')
                    log.debug(f'No data provided for {method} {url}')
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

# TODO: both brace expansion and auto coercion should be implemented by
# TODO: as identify no-op when disabled, can probably be applied much more widely
# is_enabled = conf_get(expanded, Settings.BRACE_EXPANSION)
# auto_coerce = conf_get(expanded, Settings.AUTO_COERCE)
#
# if brace_expansion:
#     brace_expander = partial(matchers.brace_expand, auto_coerce=auto_coerce)
# else:
#     brace_expander = matchers.brace_expand_noop
def brace_expand_fields(request_dict: Mapping[str,object], *keys: str) -> Dict[str, object]:
    """
    Takes a list of keys and applies brace expansion for each key it finds, others are silently ignored.
    Returns a new dict, all the other entries as well.
    If is_enabled is False, then it will simply just return a new dict without any expansion applied.
    """
    expanded = json.loads(json.dumps(request_dict))
    is_enabled = conf_get(expanded, Settings.BRACE_EXPANSION)
    auto_coerce = conf_get(expanded, Settings.AUTO_COERCE)

    if not is_enabled:
        return expanded

    for k in keys:
        field = expanded.get(k)
        if field:
            field = expand(field, auto_coerce)
            expanded[k] = field
    return expanded
