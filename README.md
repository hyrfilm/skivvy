# skivvy
A simple tool for testing JSON/HTTP APIs

Skivvy was developed in order to faciliate automated testing of web-APIs. If you've written an API that consumes or
produces JSON, skivvy makes it easy to create test-suites for these APIs.
You can think of skivvy as a more simple-minded cousin of cURL - it can't do many of the things cURL can but the the
things few things it can do it does well.

## try it out
#### installing
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
* dumping output from one testcase into a file and passing in parts of that data to other testcases
* ... and more! ;)

### Documentation

#### config documentation
a skivvy testfile, can contain the following flags that changes how the tests is performed

#### mandatory config settings
* *tests* - directory where to look for tests (recursively)
* *ext* - file extension to look for (like ".json")
* *base_url* - base URL that will be prefixed for all tests

#### optional config settings
* *log_level* - a low value like 10, shows ALL logging, a value like 20 shows only info and more severe

#### mandatory settings for a testcase
* *url* - the URL that skivvy should send a HTTP request to 
* *base_url* - an base url (like "https://example.com") that will be prefixed for the URL
* *method* - what HTTP verb should be used (optional, defaults to GET)

#### optional settings for testcase
* *brace_expansion* - whether brace expansion should used for URLs containting <variable> 
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

#### matchers

###TODO :)