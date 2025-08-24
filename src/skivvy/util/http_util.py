import requests

from . import log
from .str_util import tojsonstr

_methods = ["get", "post", "put", "patch", "delete", "options", "head", "connect"]
_session = requests.Session()


def do_request(url, method, data, upload_file, headers):
    http_verb = getattr(_session, method)
    log.debug("\n")
    log.debug("--- REQUEST ---")
    log.debug("%s: %s" % (method.upper(), url))
    if upload_file:
        log.debug( "file: %s" % upload_file)
    elif data:
        log.debug(" body: %s" % data)
    log.debug(" headers: %s" % tojsonstr(headers))
    log.debug("----------------")
    log.debug("\n")

    # it's not possible to both upload a file & provide json data
    if upload_file:
        r = http_verb(url, files=upload_file, headers=headers)
    else:
        r = http_verb(url, data=data, headers=headers)

    log.debug("\n")
    log.debug("--- RESPONSE ---")
    log.debug("status: %s" % r.status_code)
    log.debug("json: %s" % tojsonstr(as_json(r)))
    log.debug("headers: %s" % tojsonstr(dict(r.headers)))
    log.debug("----------------")
    log.debug("\n")

    return r


def as_json(response):
    try:
        return response.json()
    except:
        return None
