# try:  # python 2
#     from urllib2 import Request, urlopen
# except ImportError:  # python 3
#     from urllib import Request
#     from urllib import urlopen
import requests

import log_util

_methods = ["get", "post", "put", "patch", "delete"]


def do_request(url, method, data, headers, logger):
    http_verb = getattr(requests, method)
    logger.debug("--- REQUEST ---")
    logger.debug("%s: %s" % (method.upper(), url))
    logger.debug(" data: %s" % data)
    logger.debug(" headers: %s" % headers)
    logger.debug("----------------")

    r = http_verb(url, data=data, headers=headers)

    logger.debug("--- RESPONSE ---")
    logger.debug("%s" % r.status_code)
    logger.debug("%s" % r.json())
    logger.debug("----------------")

    return r
