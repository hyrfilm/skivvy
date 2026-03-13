# skivvy

**Integration testing for HTTP APIs. Tests are JSON. No code required.**

Skivvy is a tiny, opinionated CLI tool that lets you write API tests as plain JSON files and run them from the terminal. No JS hooks. No GUI. No snapshots. You declare what you expect, and skivvy tells you if reality disagrees — with readable diffs when it does.

It works with REST, GraphQL, and anything else that speaks HTTP. It's built for CI/CD pipelines but just as useful on your local machine.

### The core idea

Most API testing tools push you toward one of two bad patterns: writing imperative code in a language you didn't ask for, or snapshot-testing entire responses so every unrelated field change breaks your suite. Skivvy takes a different approach — **assert only what you care about**. Check the status code, a single field, a subset of a nested object, or the length of a list. Ignore the rest.

```json
{ "url": "/api/items", "response": { "results": [{ "name": "Widget42" }] } }
```

That's it. That's a test.

This works especially well with deeply nested responses like GraphQL, where you can match subsets without caring about the full envelope:

```json
{
  "url": "/graphql",
  "method": "post",
  "body": { "query": "{ posts { id title author { name } tags } }" },
  "match_subsets": true,
  "match_every_entry": true,
  "response": {
    "errors": null,
    "data": {
      "posts": [{ "author": { "name": "$text" }, "tags": "$len_gt 0" }],
      "totalCount": "$gt 0"
    }
  }
}
```

Every post must have a named author and at least one tag. No GraphQL errors. You don't have to spell out the full response shape.

Matchers can reach beyond string comparison — they can enforce constraints across entire collections:

```json
{
  "url": "/users/all",
  "match_every_entry": true,
  "response": {
    "images": [{ "thumbnail": "$valid_url", "id": "$unique" }]
  }
}
```

Every user's thumbnail is a live, reachable URL. Every ID is unique across the whole list. Two invariants over an arbitrarily large dataset, in a few lines of JSON.

### What you get

- **All the HTTP plumbing you'd expect** — every verb, headers, cookies, file uploads, form data, response chaining via variables and brace expansion
- **Subset matching** — assert against deeply nested fields without specifying the full path
- **Built-in matchers** — `$contains`, `$regexp`, `$len`, `$gt`, `$between`, `$valid_url`, `$date`, `$store`/`$fetch`, approximate values with `$~`, and more — plus automatic negation (`$!contains`) for all of them
- **Custom matchers** — drop a Python file with a `match(expected, actual)` function into a directory and it just works
- **Readable diffs** — when a test fails, you see exactly what went wrong in a human-friendly format, with multiple diff styles to choose from
- **Flexible configuration** — per-test overrides, environment configs, CLI flags, env vars, with a clear precedence order and sane defaults
- **Setup & teardown** — use directory naming and include/exclude filters to control execution order
- **Deterministic execution** — serial by default, predictable every time

### Install

```
uvx skivvy --version        # no install needed with uv
pipx run skivvy --version    # or pipx
pip install skivvy           # or plain pip
docker run --rm hyrfilm/skivvy:examples  # or docker
```

MIT license.
