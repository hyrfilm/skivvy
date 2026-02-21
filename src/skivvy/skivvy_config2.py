from typing import NamedTuple, Dict, Any, ChainMap, Mapping

from skivvy.util import file_util


class Option(NamedTuple):
    key: str
    default: Any
    help: str = ""

    def from_dict(self, config_dict: Dict[str, Any]):
        return config_dict.get(self.key, self.default)


class Settings:
    LOG_LEVEL = Option("log_level", "INFO", "Logging level")
    BASE_URL = Option("base_url", "", "Base URL for requests")
    URL = Option("url", None, "Request URL")
    BRACE_EXPANSION = Option(
        "brace_expansion", False, "Enable brace expansion (see README.md)"
    )
    VALIDATE_VARIABLE_NAMES = Option(
        "validate_variable_names",
        True,
        "Require variables to have typical syntax (start with letter, contain only alphanumerics and _-.,/\\ characters)",
    )
    AUTO_COERCE = Option(
        "auto_coerce",
        True,
        "Automatically coerce types in brace expansion, comparing values etc",
    )
    METHOD = Option("method", "get", "HTTP method")
    STATUS = Option("status", None, "Will only be checked if specified in the test")
    RESPONSE = Option("response", {}, "Expected response body")
    RESPONSE_HEADERS = Option("response_headers", None, "Expected response headers")
    HEADERS = Option("headers", None, "Request headers")
    BODY = Option("body", None, "JSON Request body")
    FORM = Option("form", None, "Form body")
    UPLOAD = Option("upload", None, "File upload configuration")
    QUERY = Option("query", None, "Query parameters")
    CONTENT_TYPE = Option("content_type", "application/json", "Request content type")
    WRITE_HEADERS = Option("write_headers", {}, "Headers to write to files")
    READ_HEADERS = Option("read_headers", {}, "Headers to read from files")
    MATCH_SUBSETS = Option(
        "match_subsets", False, "Allow subset matching in verification"
    )
    SKIP_EMPTY_OBJECTS = Option(
        "skip_empty_objects",
        False,
        "When subset matching, skip verification for empty objects",
    )
    SKIP_EMPTY_ARRAYS = Option(
        "skip_empty_arrays",
        False,
        "When subset matching, skip verification for empty arrays",
    )
    MATCH_EVERY_ENTRY = Option(
        "match_every_entry", False, "Require every actual array entry to match the expected template"
    )
    MATCH_FALSINESS = Option(
        "match_falsiness", True, "Match falsy values in verification"
    )
    COLORIZE = Option("colorize", True, "Enable colored output")
    FAIL_FAST = Option("fail_fast", False, "Stop on first failure")
    MATCHERS = Option("matchers", None, "Directory containing custom matcher files")
    MATCHER_OPTIONS = Option("matcher_options", {}, "Per-matcher configuration options")


def get_all_settings() -> list[Option]:
    return [
        option for _name, option in vars(Settings).items() if isinstance(option, Option)
    ]


def create_test_config(*dicts: Dict[str, object]) -> Mapping[str, object]:
    """Creates a dict-like test configuration from multiple dictionaries
    Priority order:
    1. command-line arguments
    2. current test fields
    3. config file
    4. default values
    """
    defaults = {
        option.key: option.default for option in get_all_settings() if option.default
    }
    priority = [*dicts, defaults]
    d = ChainMap({}, *priority)
    return dict(**d)


def conf_get(d, option: Option):
    return d.get(option.key, option.default)


def create_testcase(*sources: Dict[str, object] | str) -> Mapping[str, object]:
    """Creates a testcase by merging any number of configurations into one single object.
    A source can either be a string or a dict, strings will be interpreted as paths to json files, the
    output is created by merging and potentially overriding fields by creating a chained map.
    """
    dicts: list[Dict[str, object]] = []
    for source in sources:
        if isinstance(source, str):
            source_dict = file_util.parse_json(source)
        elif isinstance(source, dict):
            source_dict = source
        elif hasattr(source, "as_dict") and callable(getattr(source, "as_dict")):
            source_dict = source.as_dict()
        else:
            source_dict = dict(source)

        dicts.append(source_dict)

    return create_test_config(*dicts)
