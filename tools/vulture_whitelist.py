# Vulture whitelist for static-analysis false positives (tooling only, not runtime code).
# Settings Options are accessed dynamically via get_all_settings() / conf_get()
# and through string keys in config dicts, so vulture cannot trace their usage.

from skivvy.config import Settings

Settings.LOG_LEVEL
Settings.STATUS
Settings.RESPONSE
Settings.RESPONSE_HEADERS
Settings.MATCH_SUBSETS
Settings.MATCH_FALSINESS
Settings.DIFF_ENABLED
Settings.DIFF_NDIFF
Settings.DIFF_UNIFIED
Settings.DIFF_TABLE
Settings.DIFF_FULL
Settings.DIFF_COMPACT_LISTS
Settings.HTTP_REQUEST_LEVEL
Settings.HTTP_RESPONSE_LEVEL
Settings.HTTP_HEADERS_LEVEL
Settings.FAIL_FAST
Settings.FILE_ORDER
Settings.MATCHERS

# Option.help is used dynamically (e.g. for --settings output)
_.help  # type: ignore

# Used in tests (test_scope.py) for inspection
from skivvy.util import scope
scope.dump

# Intentionally kept with TODO markers — vulture flags them but they're annotated
from skivvy.util import dict_util
dict_util.get_many
dict_util.filter_null_from_dict
scope.get_all_namespaces
