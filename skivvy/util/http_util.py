# try:  # python 2
#     from urllib2 import Request, urlopen
# except ImportError:  # python 3
#     from urllib import Request
#     from urllib import urlopen
import requests

from str_util import tojsonstr

_methods = ["get", "post", "put", "patch", "delete"]
_session = requests.Session()


def do_request(url, method, data, upload_file, headers, logger):
    http_verb = getattr(_session, method)
    logger.debug("--- REQUEST ---")
    logger.debug("%s: %s" % (method.upper(), url))
    logger.debug(" data: %s" % data)
    logger.debug(" headers: %s" % headers)
    logger.debug("----------------")

    # it's not possible to both upload a file & provide json data
    if upload_file:
        r = http_verb(url, files=upload_file, headers=headers)
    else:
        r = http_verb(url, data=data, headers=headers)

    logger.debug("--- RESPONSE ---")
    logger.debug("%s" % r.status_code)
    logger.debug("%s" % tojsonstr(as_json(r)))
    logger.debug("----------------")

    return r


def as_json(response):
    try:
        return response.json()
    except:
        return None
