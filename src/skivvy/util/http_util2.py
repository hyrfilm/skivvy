from typing import Dict, Any

import requests
from requests import Response

_session = requests.Session()

def initialize_session(session=None):
    global _session
    _session = session or requests.Session()

def do_request(method, payload: Dict[str, Any]) -> Response:
    request_function = getattr(_session, method)
    assert callable(request_function), f"Session function {method} is not callable"
    r = request_function(**payload)
    return r
