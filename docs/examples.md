### Examples

The [playground](https://hyrfilm.github.io/skivvy/) lets you try every example below directly in the browser — each link opens a pre-configured test suite you can edit and re-run.

#### [Basics](https://hyrfilm.github.io/skivvy/?category=basics)

Simple REST requests: list a collection, fetch a single resource by ID, and assert on a 404. Covers status codes, array length checks (`$len`), and substring matching (`$contains`).

#### [Matchers](https://hyrfilm.github.io/skivvy/?category=matchers)

A tour of the full matcher library. Numeric comparisons (`$gt`, `$lt`, `$between`), approximate values (`$~`), strings (`$contains`, `$regexp`, `$text`), array and string length bounds (`$len_gt`, `$len_lt`), set membership (`$in`), format validators (`$uuid`, `$valid_ip`), negation (`$!contains`, `$!regexp`), inline Python expressions (`$expr`), and combining `match_subsets` with `match_every_entry` for collection-level assertions.

#### [Variables](https://hyrfilm.github.io/skivvy/?category=variables)

Chaining requests through stored values. `$store` captures a field from one response, brace expansion (`<variable>`) injects it into subsequent URLs or bodies, and `$fetch` asserts that a value still matches what was stored. Also demonstrates `$write_file` / `$read_file` for persisting data to disk between tests.

#### [OAuth](https://hyrfilm.github.io/skivvy/?category=oauth)

A realistic multi-step auth flow: POST credentials to a login endpoint, `$store` the access and refresh tokens, then use `<access_token>` in an `Authorization` header to hit a protected profile endpoint, and finally exchange the refresh token for a new one. Shows how variable chaining turns sequential API calls into a declarative workflow.

#### [Headers](https://hyrfilm.github.io/skivvy/?category=headers)

Reading and writing HTTP headers. Assert on response headers like `Content-Type`, send custom request headers (`Accept`, `X-Request-ID`), and combine an `Authorization` header with response-body assertions — including `$in` for checking set membership.

#### [GraphQL](https://hyrfilm.github.io/skivvy/?category=graphql)

Testing GraphQL endpoints over POST. Uses `match_subsets` to assert on specific nested fields without spelling out the full response shape, `match_every_entry` to enforce invariants across every item in a list, and `errors: null` to verify clean execution. Matchers like `$between`, `$text`, and `$len_gt` work naturally inside deeply nested structures.

#### [Diffs](https://hyrfilm.github.io/skivvy/?category=diffs)

Intentionally failing tests that showcase skivvy's diff output. One test returns a mismatched response body, the other expects the wrong status code — both produce human-readable diffs so you can see exactly what went wrong.
