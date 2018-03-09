# skivvy
A simple tool for testing JSON/HTTP APIs

Skivvy was developed in order to faciliate automated testing of web-APIs. If you've written an API that consumes or
produces JSON, skivvy makes it easy to create test-suites for these APIs.
You can think of skivvy as a more simple-minded cousin of cURL - it can't do many of the things cURL can but the the
things few things it can do it does well.

## EXAMPLE USAGE HERE

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
curl https://github.com/hyrfilm/skivvy/raw/master/skivvy_examples.zip -OL skivvy_examples.zip
tar xf skivvy_examples.zip
```
* run:
```sh
skivvy run cfg/example.json
```
