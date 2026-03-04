from typing import Dict, Callable
import requests
from skivvy.util import dict_util, file_util
from skivvy import events
from dataclasses import dataclass
from typing import Mapping, Any, Optional
import json
from skivvy.util.str_util import tojsonstr

_supported_methods = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
    "connect",
}
_session = None
_NO_BODY_STATUS = {204, 205, 304}


@dataclass(frozen=True, slots=True)
class HttpEnvelope:
    """Immutable container for an HTTP response with lazy/optional JSON parsing."""

    status_code: int
    headers: Mapping[str, str]
    text: str
    encoding: str
    url: str
    elapsed: float

    def has_body(self) -> bool:
        return len(self.text) > 0

    def content_type(self) -> str:
        return self.header("Content-Type", "")

    def json(self) -> Optional[Any]:
        """
        Returns parsed JSON, or None if:
        - body is empty
        - parsing fails (ValueError)
        """
        if not self.has_body():
            return None
        if len(self.text.strip()) == 0:
            return None

        try:
            return json.loads(self.text)
        except ValueError:
            return None

    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        # case-insensitive lookup
        for k, v in self.headers.items():
            if k.lower() == name.lower():
                return v
        return default

    @staticmethod
    def from_requests(resp: requests.Response) -> "HttpEnvelope":
        return HttpEnvelope(
            status_code=getattr(resp, "status_code", 0),
            headers=getattr(resp, "headers", {}),
            text=getattr(resp, "text", ""),
            encoding=getattr(resp, "encoding", "utf-8"),
            url=getattr(resp, "url", ""),
            elapsed=getattr(resp, "elapsed", -1),
        )


def initialize_session(session=None):
    global _session
    _session = session or requests.Session()


def execute(request: dict[str, object]) -> HttpEnvelope:
    method, payload = prepare_request_data(request)
    payload = prepare_upload_files(payload)
    r = do_request(method, **payload)
    events.emit(
        events.HTTP_RESPONSE,
        http_status=getattr(r, "status_code", None),
        url=getattr(r, "url", payload.get("url")),
        response_headers=dict(getattr(r, "headers", {}) or {}),
        response_body=getattr(r, "text", ""),
    )
    return HttpEnvelope.from_requests(r)


def prepare_request_data(request_data: dict[str, object]) -> tuple[str, dict]:
    remap = {"form": "data", "upload": "files", "query": "params", "body": "json"}
    request_data = dict_util.remap_keys(request_data, remap)
    method = request_data.pop("method", "").lower()
    return method, request_data


def prepare_upload_files(payload: dict[str, object]) -> dict[str, object]:
    files = payload.get("files", {})
    prepared_files = {
        field: (
            file_util.strip_filename(filename),
            file_util.read_file_contents(filename, binary=True),
        )
        for field, filename in files.items()
    }

    next_payload = dict(payload)
    next_payload["files"] = prepared_files
    return next_payload


def do_request(method, **payload: Dict[str, Any]) -> requests.Request:
    assert method, "missing method"
    assert method in _supported_methods, f"unsupported method: {method}"

    request_function: Callable = getattr(_session, method)
    assert callable(request_function), f"Session function {method} is not callable"
    files = payload.get("files")
    upload_fields = list(files.keys()) if isinstance(files, dict) else None
    events.emit(
        events.HTTP_TRANSPORT,
        http_method=method,
        url=payload.get("url"),
        request_headers=dict(payload.get("headers") or {}),
        request_query=payload.get("params"),
        request_json=payload.get("json"),
        request_data=payload.get("data"),
        request_upload_fields=upload_fields,
    )
    return request_function(**payload)


initialize_session()
