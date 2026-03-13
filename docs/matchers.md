| Matcher | Description |
| --- | --- |
| `$store` | Store actual value under a name for later use. E.g. $store myToken |
| `$fetch` | Assert actual equals a previously stored value. E.g. $fetch myToken |
| `$valid_url` | Assert actual is a reachable URL. Options: unsafe, prefix <url>. E.g. $valid_url unsafe |
| `$contains` | Assert actual contains expected as a substring. E.g. $contains hello |
| `$len` | Assert length of actual equals expected. Supports ~ for approximate. E.g. $len 5 |
| `$len_gt` | Assert length of actual is greater than expected. E.g. $len_gt 3 |
| `$len_lt` | Assert length of actual is less than expected. E.g. $len_lt 10 |
| `$~` | Assert actual is approximately equal to expected. Supports threshold modifier. E.g. $~ 100 or $~ 100 threshold 0.1 |
| `$gt` | Assert actual is greater than expected number. E.g. $gt 5 |
| `$lt` | Assert actual is less than expected number. E.g. $lt 100 |
| `$between` | Assert actual is between two numbers (inclusive). E.g. $between 1 10 |
| `$date` | Assert actual matches expected date. Supports: today. E.g. $date today |
| `$write_file` | Write actual value to a named temp file. E.g. $write_file token.txt |
| `$read_file` | Assert actual equals the contents of a file. E.g. $read_file token.txt |
| `$valid_ip` | Assert actual is a valid IPv4 or IPv6 address. |
| `$expects` | Assert a Python expression using 'actual' evaluates to True. E.g. $expr actual > 0 |
| `$text` | Assert actual contains only printable text characters. |
| `$uuid` | Assert actual is a valid UUID, optionally a specific version. E.g. $uuid or $uuid 4 |
| `$in` | Assert actual equals one of the space-separated values. E.g. $in active inactive pending |
| `$regexp` | Assert actual matches a regular expression. E.g. $regexp ^[A-Z]{3}$ |
| `$expr` | Assert a Python expression using 'actual' evaluates to True. E.g. $expr actual > 0 |
| `$unique` | Assert actual is unique across all values at this path in the collection. |
| `$asc` | Assert values at this path are in ascending order across the collection. |
| `$desc` | Assert values at this path are in descending order across the collection. |