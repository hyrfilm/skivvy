from typing import NamedTuple, Dict, Any, ChainMap, Mapping


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
    BRACE_EXPANSION = Option("brace_expansion", False, "Enable brace expansion (see README.md)")
    AUTO_COERCE = Option("auto_coerce", True, "Automatically coerce types in brace expansion, comparing values etc")
    METHOD = Option("method", "get", "HTTP method")
    STATUS = Option("status", None, "Will only be checked if specified in the test")
    RESPONSE = Option("response", {}, "Expected response body")
    BODY = Option("body", None, "JSON Request body")
    FORM = Option("form", None, "Form body")
    UPLOAD = Option("upload", None, "File upload configuration")
    CONTENT_TYPE = Option("content_type", "application/json", "Request content type")
    WRITE_HEADERS = Option("write_headers", {}, "Headers to write to files")
    READ_HEADERS = Option("read_headers", {}, "Headers to read from files")
    MATCH_SUBSETS = Option("match_subsets", False, "Allow subset matching in verification")
    MATCH_FALSINESS = Option("match_falsiness", True, "Match falsy values in verification")
    COLORIZE = Option("colorize", True, "Enable colored output")
    FAIL_FAST = Option("fail_fast", False, "Stop on first failure")
    MATCHERS = Option("matchers", None, "Directory containing custom matcher files")


def create_test_config(*dicts: Dict[str, object]) -> Mapping[str, object]:
    """Creates a dict-like test configuration from multiple dictionaries"""
    return ChainMap(*dicts)

def conf_get(d, option: Option):
    return d.get(option.key, option.default)
