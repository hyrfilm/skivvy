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
mkdir skivvy
cd skivvy
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
