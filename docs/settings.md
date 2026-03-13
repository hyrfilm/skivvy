| Setting | Default | Description |
| --- | --- | --- |
| `log_level` | `INFO` | Logging level |
| `base_url` | `` | Base URL for requests |
| `url` | `` | Request URL |
| `brace_expansion` | `False` | Enable brace expansion (see README.md) |
| `brace_expansion_warnings` | `True` | Log a warning when brace expansion fails to resolve a variable |
| `brace_expansion_strict` | `False` | Raise an exception when brace expansion fails to resolve a variable |
| `validate_variable_names` | `True` | Require variables to have typical syntax (start with letter, contain only alphanumerics and _-.,/\ characters) |
| `auto_coerce` | `True` | Automatically coerce types in brace expansion, comparing values etc |
| `method` | `get` | HTTP method |
| `status` | `` | Will only be checked if specified in the test |
| `response` | `{}` | Expected response body |
| `response_headers` | `` | Expected response headers |
| `headers` | `` | Request headers |
| `body` | `` | JSON Request body |
| `form` | `` | Form body |
| `upload` | `` | File upload configuration |
| `query` | `` | Query parameters |
| `content_type` | `application/json` | Request content type |
| `write_headers` | `{}` | Headers to write to files |
| `read_headers` | `{}` | Headers to read from files |
| `match_subsets` | `False` | Allow subset matching in verification |
| `skip_empty_objects` | `False` | When subset matching, skip verification for empty objects |
| `skip_empty_arrays` | `False` | When subset matching, skip verification for empty arrays |
| `match_every_entry` | `False` | Require every actual array entry to match the expected template |
| `match_falsiness` | `True` | Match falsy values in verification |
| `diff_enabled` | `True` | Enable diff output for failures |
| `diff_ndiff` | `True` | Show ndiff view for failure diffs |
| `diff_unified` | `False` | Show unified diff view for failures |
| `diff_table` | `False` | Show side-by-side table diff view |
| `diff_full` | `False` | Show full expected/actual payloads without projection or compaction |
| `diff_compact_lists` | `True` | Compact very long actual lists in failure diffs |
| `http_request_level` | `DEBUG` | Log level for request method/url/payload output (set null/OFF to disable) |
| `http_response_level` | `DEBUG` | Log level for response status/body output (set null/OFF to disable) |
| `http_headers_level` | `DEBUG` | Log level for request/response header output (set null/OFF to disable) |
| `fail_fast` | `False` | Stop on first failure |
| `file_order` | `lexical` | Test file ordering: lexical (default) or natural |
| `matchers` | `` | Directory containing custom matcher files |
| `matcher_options` | `{}` | Per-matcher configuration options |
| `ext` | `.json` | File extension for test files |
| `timing` | `False` | Enable timing output for each test |
| `http_timing` | `False` | Enable HTTP transport timing breakdown |
| `timeout` | `30` | HTTP request timeout in seconds |
| `fixed_column_width` | `` | Fixed column width for test result lines (default: terminal width) |
| `failed_summary` | `True` | Print a summary of all failed test paths at the end of the run |
| `column_overflow` | `ellipsis` | How to handle test file paths that exceed the column width: "fold", "crop", "ellipsis", "ignore" |
| `passed_style` | `green4` | Rich style for passed test file path (e.g. "bold green", "" to disable) |
| `failed_style` | `red` | Rich style for failed test file path (e.g. "bold red", "" to disable) |