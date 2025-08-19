# Skivvy — JSON-native, CLI-first integration tests for HTTP APIs

Skivvy is a tiny, Unix-style runner for API tests where the tests themselves are **JSON**.

### What makes skivvy similar to postman / bruno / curl / jq / etc

- Support for all https-verbs, http-headers, cookies handled the way you expect them to, data from responses can be passed into other requests, easy to deal with things such as OAuth etc
- Rich support for verifying / asserting repsonses
- Good diffs when tests fail
- Setup / Teardown functionality
- Arbitary amount environment configs (eg local / staging / etc)

### What makes skivvy *different* (compared to postman, bruno)

- Assert **only what you care about** (whether it's only the status, or a substring in the response, or a particular field among other fields you don't care about - snapshots are an anti-pattern leading to brittle, flaky-tests and false positives). This is probably the most central and distinguishing aspect of skivvy and
although technically can do snapshot-like asserting, it's strongly discouraged and if that's something you're
after you should probably stick to some other tool.
- Unix-philosophy: do one thing well
- Lightweight
- Simple, clear, declarative, text-based (.json) tests. Much simpler than postman, bruno etc
- CI-friendly, no GUI
- Very tiny API (if it could even be called that)
- Simple to extend by implementing tiny custom python functions
- Predictable deterministic execution
- MIT license

At [my current company](https://www.mindmore.com/) we use it for **all backend API tests** - as far as I know there's never been a false positive (hello cypress).

## Why Skivvy (vs GUI suites)
GUI tools (Postman/Bruno) are good for exploration, but heavier and brittle when used in an actual CI/CD envirionment for testing your entire API. But what's worse is they push you toward bad habits such as overerly complicated imperative JS hooks and snapshot-style assertions. This is just unnecessary and encourages writing bad, brittle tessts. Having JS code does also introduce its own set of issues like learning an some unwieldy API using an unwieldy languange like JS (this is not meant as a flame-bait ;) I happpen to write JS-code for a living but that doesn't have to mean that I think it's a good languange for all tasks). 
Skivvy tests are plain json files you keep in git.

## Quick look

Status only:
```json
{ "url": "https://api.example.com/ping", "status": 200 }
```

Assert what you care about:
```json
{
  "url": "https://api.example.com/items",
  "response": {
    "results": [{ "name": "Widget42" }]
  }
}
```

Or maybe you just care about:
```json
{
  "url": "https://api.example.com/items",
  "response": {
    "results": ""results": "$len 200""
  }
}
```


Pass state between steps (files + brace expansion):
```json
{
  "_comment": "Login and store dashboard path",
  "url": "/login",
  "method": "post",
  "response": {
    "status": 200,
    "dashboard": "$write_file dashboard.txt",
    "profile": { "pic": "$valid_url" }
  }
}
```
```json
{ "url": "/home/<dashboard.txt>", "status": 200 }
```

Match a **subset** anywhere under a node:
```json
{
  "url": "/project",
  "response": { "project": { "name": "MKUltra" } }
}
```
(Works even if the server nests it under `project.department.name`.)
This can be disabled globally or per tests, if so preferred.

## Why not just curl + jq + bash?
Well...You can — and you’ll slowly re-invent like skivvy (reusable assertions, readable diffs, state passing, config/env handling, CI output). Skivvy is the minimal framework you’d build anyway.

## Readable diffs
Intentional failure:
```json
{
  "url": "/project",
  "match_subsets": true,
  "response": { "project": { "name": "WrongName" } }
}
```
Typical output (abridged):
```
✗ GET /project
  response.project.name
    expected: "WrongName"
    actual:   "MKUltra"
    diff:
      - WrongName
      + MKUltra
```

**Docker**
The preferred to run it:
```bash
docker run --rm hyrfilm/skivvy skivvy run --version
docker run --rm -v "$PWD":/app -w /app hyrfilm/skivvy skivvy run cfg.json
```

## Install & Run
Or through pip:
**pip**
```bash
pip install skivvy
skivvy run cfg/example.json
```

## CLI filters (this example illustrates how a setup/teardown could be implemented)
```bash
skivvy run cfg.json -i '00_setup' -i '99_teardown' -e 'flaky' -i $1
```
Then you can just create an alias for it and be able to do something like:
```bash
skivvy 01_login_tests
```
In your local / CI environment you could, for example, seed the database in the setup and tear it down after running the test pattern you specified
Includes are applied first, then excludes.

## Config (high-value keys)
A minimal config / env file might look this:
```json
{
  "tests": "./api/tests",
  "base_url": "https://example.com",
  "ext": ".json"
}

Or specifying all currently supported settings:
```
  "ext": ".json",
  "base_url": "https://api.example.com",
  "colorize": true,
  "fail_fast": false,
  "brace_expansion": true,
  "auto_coerce": true,
  "matchers": "./matchers"
```

## Test file keys (most used)
- `url` (string required), 
### All other fields are optional
- `method` (`get` default),
- `status` (expected HTTP status, only checked if specified)
- `response` (object or matcher string, only checked if specified)
- `data` (body), `headers`, `content_type`, `json_encode_body`
- `match_subsets` (true by default, allows you to check fields or parts of objects, occurring somewhere in the response)
- `match_falsiness` (true by default)
- `brace_expansion`, (true by default, makes skivvy look for the content of files specified within <some_file.txt> eg /item/<item.txt> will be transformed into /item/42 if this was the content of item.txt - the .txt is just a convention by a recommended one)
- `auto_coerce` - will try to interpret something like "field": "<item.txt>" as number, boolean, otherwise it will passed in as text
- `_comment` or `comment` or `note` or `whatever` (unrecognized top-level entries are simply ignored)

## Built-in matchers (common)
Format: `"$matcher args..."`

- `$contains <text>` — substring present
- `$len N`, `$len_gt N`, `$len_lt N` — length checks
- `$valid_url` — value is http(s) URL that returns 2xx
- `$regexp <pattern>` — regex match
- `$~ <number> [threshold <ratio>]` — approximate numeric
- `$date [format?]` — value parses as date
- `$expr <python_expr>` — escape hatch (`actual` bound to value)
- `$write_file <filename>` — write value for later `<filename>`
- `$read_file <filename>` — read value from file

Negation: prefix with `$!` (e.g., `$!contains foo`).

**Custom matchers:** create `./matchers/<name>.py` with:
```python
def match(expected, actual):
    # return True/False, optionally with a message
    ...
```

## Examples: JSONPlaceholder
See `examples/jsonplaceholder/` in this repo.

## Asciinema (30s success + 15s failure)
```bash
# success
cd examples/jsonplaceholder
asciinema rec demo.cast -c "bash -lc 'skivvy -c config.json tests'"
# failure diff
asciinema rec demo_fail.cast -c "bash -lc 'skivvy -c config.json tests/99_fail_diff_demo.json'"
```

## Docker & ephemeral DBs
We often seed a DB in `00_setup/` and teardown in `9999_teardown/`. With bind mounts, state files (IDs/tokens) are inspectable:
```bash
docker run --rm -v "$PWD":/work -w /work hyrfilm/skivvy skivvy -c cfg.json tests
```

## FAQ
- **Isn’t this just curl + jq / grep ?** YES, it is. Especially if you like writing a lot of bash, over time you might want reusable assertions, diffs, state, filters, CI-friendly output, and then you've ended up re-implementing something like skivvy or not, I say go for it!
- **Why JSON (not YAML/JS)?** JSON matches your payloads; zero DSL. JS is not support as a concious decision,
if you want a non-declarative tool for testing your APIs, there's always bruno/postman etc.
- **Why serial by default?** Determinism is a feature. For concurrency, run multiple processes with distinct state dirs. (This might get elevated to support true concurrency in the future, if the total cost of complexity is low and
fits with the other design-goals mentioned above).
- **Comments?** `_comment` is supported and ignored at runtime.

## License

Keeping it MIT dude
Keep rockin' in the free world
# skivvy
A simple tool for testing JSON/HTTP APIs

Skivvy was developed in order to faciliate automated testing of web-APIs. If you've written an API that consumes or
produces JSON, skivvy makes it easy to create test-suites for these APIs.
You can think of skivvy as a more simple-minded cousin of cURL - it can't do many of the things cURL can - but the few things it can do it does well.

## try it out
#### running it through docker
This is the simplest and the recommended way to run it
```sh
docker run --rm hyrfilm/skivvy skivvy run --version
```
See below for a more useful example on how to run it using bind mounts.

#### installing it manually
* install through PIP
```sh
pip install skivvy
```
* download some examples
```sh
mkdir skivvy_examples
cd skivvy_examples
curl -OL https://github.com/hyrfilm/skivvy/raw/master/skivvy_examples.zip
tar xf skivvy_examples.zip
```
* run:
```sh
skivvy run cfg/example.json
```

#### running skivvy through docker (using bind mounts)
Assuming the current directory would contain your tests and that the root of that directory would contain a
configuration file `cfg.json` you could bind mount that directory and run skivvy like so:
```sh
docker run --rm --mount type=bind,source="$(pwd)",target="/app" hyrfilm/skivvy skivvy run cfg.json
```

## what you can do with it

Let's say you've created an API for looking up definition of words. Calling the URL: ```http://example.com/words/api/skivvy``` would result in this being returned:

```json
{"word": "skivvy",
"results": [{
  "definition": "a female domestic servant who does all kinds of menial work",
  "type": "noun",
  "language": "English",
  "dialect": "British"
  }]
}
```
With skivvy you could easily create a testcase for this in a myraid of ways depending on what you would want to test:
#### checking the HTTP status-code
```json
{"url": "http://example.com/words/api/skivvy",
"status": 200}
```
#### checking fields
```json
{"url": "http://example.com/words/api/skivvy",
"response": {
   "results": [{
   "type": "noun",
   "language": "English"
   }]
}
```
#### checking the length of the results
```json
{"url": "http://example.com/words/api/skivvy",
"response": {
  "results": "$len 1"
  }
}
```
#### checking that the response contain some particular data
```json
{"url": "http://example.com/words/api/skivvy",
"response": "$contains servant who does all kinds of menial work"}
```

#### etc
Other things supported:
* test-suites incl using different environments (like staging / production)
* custom matcher syntax, for checking things like urls (```$valid_url```), approximations (```$~```), date-validation (```$date```), custom python-expression (```$expr```) and more
* ability to create extend the syntax to create own matchers easily
* all common http-verbs (get, put, post, delete)
* reading and writing http-headers
* file uploads
* dumping output from one testcase into a file and passing in parts of that data to other testcases
* your own custom matchers
* ... and more! ;)

## Documentation
**NOTE:** The easiest way to gain understanding of ways to use skivvy is to simply download the examples and _then_ look at the documentation.

All examples as zip: https://github.com/hyrfilm/skivvy/raw/master/skivvy_examples.zip
Or if you prefer to view them on github directly: https://github.com/hyrfilm/skivvy/tree/master/skivvy/examples

### CLI flags
As common for most testing frameworks, you can pass a number of flags to filter what files get included in the suite
that skivvy runs. `-i regexp` is used for including files, `-e regexp`is used for excluding files.

Running `skivvy run cfg.json -i file1 -i file2` only includes paths that match either the regexp `file1` or `file2`. `skivvy run cfg.json` is functionally 
equivalent of `skivvy run cfg.json -i *.` In other words, all files that skivvy finds are included.

Running `skivvy run cfg.json -e file3` excludes paths that match the `file3` regexp.

Stacking multiple flags is allowed: `skivvy run cfg.json -i path1.* -i path2.* -e some.*file`.
The order of filtering is done by first applying the `-i` filters and then the `-e` filters.

### config settings
a skivvy testfile, can contain the following flags that changes how the tests is performed:

##### mandatory config settings
* *tests* - directory where to look for tests (recursively)
* *ext* - file extension to look for (like ".json")
* *base_url* - base URL that will be prefixed for all tests

##### optional config settings
* *log_level* - a low value like 10, shows ALL logging, a value like 20 shows only info and more severe
* *colorize* - terminal colors for diffs (default is true)
* *fail_fast* - aborts the test run immediately when a testcase fails instead of running the whole suite (default is false) 
* *matchers* - directory where you place your own matchers (eg "./matchers")

#### mandatory settings for a testcase
* *url* - the URL that skivvy should send a HTTP request to 
* *base_url* - an base url (like "https://example.com") that will be prefixed for the URL
* *method* - what HTTP verb should be used (optional, defaults to GET)

#### optional settings for testcase
* *brace_expansion* - whether brace expansion should used for URLs containing \<variable> (these variables can be retrieved from a file in the path, or can be a file created using $write_file)
* *expected_status* - the expected HTTP status of the call
* *response* - the _expected_ response that should be checked against _actual_ response received from the API
* *data* - data should be sent in in POST or PUT request
* *json_encode_body* - setting this to false makes skivvy not json encode the body of a PUT or POST and instead sends it as form-data
* *headers* - headers to send into the request
* *content_type* - defaults to _"application/json"_
* *headers_to_write* - headers that should be retrieved from the HTTP response and dumped a file, for example: ````"write_headers": {"headers.json": ["Set-Cookie", "Cache-Control"]}, ````
* *headers_to_write* - specifies a file containing headers to be sent in the request, for example: ````"read_headers": "headers.json"````
* *match_subsets* - (boolean, default is false) - controls whether skivvy will allow to match a subset of a dict found in a list
* *match_falsiness* - (boolean, default is false) - controls whether skivvy will consider falsy values (such as null, and empty string, etc) as the same equivalent
* *upload* - see below for an example of uploading files
* auto_coerce - default is true, if the content of a file (read using [$read_file](#read_file) or [brace expansion](#brace-expansion)) can be interpreted as an integer it will be converted to that.

#### variables
Parts of a request may need to vary depending on context. Skivvy provides a number of ways to facilitate this:
* *If a response* contains a value you want to store, use
[$write_file](#$write_file)
* *If a response* contains a value you want to verify matches a value in a stored file, use [$read_file](#$read_file)
* If the *body of a request* should contain one or more values from a stored file, use [brace expansion](#brace-expansion)
* If the parts of the *url of a request* should contain one or more values from a stored file, use [brace expansion](#brace-expansion)
* If the *headers of a response* should be saved to a file, use $write_headers
* If the *headers of a request* should be read from a file, use $read_headers

#### brace expansion
```json
{
  "url": "http://example.com/<some>/<file>", 
  "a": "<foo>", 
  "b": "<bar>"
}
```

If you `brace_expansion` is to `true`. The value for `a` will be read from the file `foo` the value for `b`will be read from `bar`.
The first part of the path of the url will be read replaced with the contents of the file `some` and the second part by the contents of the file `file`. The file is expected to be in the path, otherwise no brace expansion will occur and the value is set as-is.
By default any value that can be interpreted as an integer will be coerced to an int. Disable this by setting `auto_coerce`to false.

#### file uploads
POSTs supports both file uploading & sending a post body as JSON. You can't have both (because that would result in conflicting HTTP-headers).
Uploads takes precedence, which means that if you have enabled file uploads for a testcase it will happily ignore the POST data you pass in.
Enabling a file upload would look like this:
```json
{
  "url": "http://example.com/some/path", 
  "upload": {"file": "./path/to/some/file"}
}
```
When seeing an upload field skivvy like above skivvy will try to open that file and pass it along in the field specified ("file"
in the example above). Currently only one upload is supported.
The file needs to either be a absolute path or relative to where skivvy is executing. If the file can't be found skivvy will
complain and mark the as failed.

### matchers

Skivvy's matcher-syntax is a simple, extensible notation that allows one greater expressiveness than vanilla-JSON would allow for.

For example, let's say you want to check that the field "email" containing a some characters followed by an @-sign,
some more characters followed by a dot and then some more characters (I don't recommend this as a way to check if an email is valid, but let's just pretend it was that simple).
Then you could write:
```
"email": "$regexp (.+)@(.+)\.(.+)"
```
The format for all matchers are as following:
```
$matcher_name expected [parameter1 parameter2... parameterN].
```
The amount of parameters a particular matcher takes depends on what matcher you are using. Currently these matchers are supported out-of-the-box:

### Extending skivvy
Skivvy can be extended with custom matchers, written in python. This allows you to either provide your own
matchers if you feel that some are missing. A matcher is just a python-function that you write yourself, you
can use all the typical python functions in the standard library like os, urllib etc.
A matcher is expected to a boolean and a message, or just a boolean if you're lazy. You're recommended to
provide a message in case the matcher returns false which will make skivvy treat that testcase as failed.
Tecnically a matcher can do whatever you want (like `$write_file`, for example) as long as it returns a boolean.

#### Example: creating a custom matcher
Let's say you want to have a sort of useless matcher that looks for whether the json has a key that contains the 
word "dude". You would use it like this `$dude nickname` that would verify that the response would have a key 
`nickname` that would contain `dude`.

1. in the config create a key like so `./matchers`
2. Create a directory, `./matchers` next to the config directory
3. Create a file `dude.py` like so:
```python
def match(expected, actual):
    expected = str(expected) # would contain "nickname"
    actual = actual # would contain json like {nicknamne: "dude", ...}
    field = actual.get(expected.strip(), {})
    if not field:
      return False, "Missing key: %s" % expected

    return "dude" in field, "Didn't find 'dude' in %s" % expected
```
4. Use it in a testcase:
```json
  {"url": "/some/url",
  "method": "get",
  "status": 200,
  "response": "$dude nickname"}
```
**NOTE:** If you were to use the matcher on a specific field, `actual` would refer to that part of the response
like this for example:
`
{
...
    response": {"somekey": "$dude"}}
`
... then the variable `actual` would refer to what `somekey` contains when the matcher would run.

### matcher reference

#### $valid_url
Matches any URL that returns a 200 status.
Example:
```
"some_page": "$valid_url"
```
would pass if `some_page` was `http://google.com`

#### $contains
Matches a string inside a field, good for finding nested information when you
don't care about the structure of what's returned.
Example:
```"foo": "$contains dude!" ```
would for example pass if `foo` was 
```json
{"movies": [{"title": "dude! where's my car?"}]}
```
#### $len
Matches the length on JSON-array.
Example:
```"foo": "$len 3" ```
would for example pass if `foo` was
```json
["a", "b", "c"]
```
#### $len_gt
Passes if the length of an JSON-array is longer than a certain amount.
Example:
```"foo": "$len_gt 3" ```
would for example pass if `foo` was
```json
["a", "b", "c", "d"]
```
#### $len_lt
Passes if the length of an JSON-array is shorter than a certain amount.
Example:
```"foo": "$len_gt 3" ```
would for example pass if `foo` was
```json
["a", "b"]
```
#### $~
Matches an approximate value.
Example:
```
"foo": "$~ 100 threshold 0.1"
```
would match values between 90-110.
#### $write_file
Writes the value of a field to a file, which can then be passed to another test.
This is useful for scenarios where you want to save a field (like a database id) that
should be passed in to a subsequent test.
Example:
```
"foo": "$write_file dude.txt"
```
Would write the value of `foo` to the file `dude.txt`

#### $read_file
Reads the value of a file and sets a field to it (most useful in the body of a POST)
```json
...
"body": {
  "foo": "$read_file dude.txt"
}
```
Would read the contents of the file `dude.txt` and assign it to the field `foo`.

#### $regexp
Matches using a regular expression.
Example:
```"foo": "$regexp [a-z]+" ```
Would require `foo` to contain at least one occurence of the a or b... to z.

#### $expr
Dynamically evaluates the string as a python statement, on the data received if the statement evaluates to True it passes.
(Be careful with this one, don't use it on untrusted data etc :)
Example:
```
"foo": "$expr (int(actual)%3)==0"
``` 
Would try to convert the data in the field `foo` to an integer and see if it was
evenly dividable by 3. If so it would pass, otherwise fail.

#### negation
Note that all matchers (including custom ones) automatically gets a negating matcher. For example, there's a matcher
called `$contains` that checks that the result contains some text string, like so `$contains what's up?`. This would
succeed if the response contained the string "what's up?". The negating matcher would look like this: 
`$!contains what's up?` - and will succeed if the response does NOT contain the string "what's up?". It operatates
as a NOT expression, in other words. The prefix used is `$!` is used instead of `$`. This will work even for
custom matchers that you create yourself.
