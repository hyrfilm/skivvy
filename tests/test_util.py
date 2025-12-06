import json


def identity(x):
    return x


def json_transform_str(data, transform=identity, sort_keys=True):
    """
    Dump a mapping to a JSON string, optionally apply a transform function,
    and return the resulting JSON string.

    data: mapping (e.g. dict) to serialize.
    transform: optional function taking and returning a JSON string.
    sort_keys: sort keys for deterministic output (default True).
    """
    s = json.dumps(data, sort_keys=sort_keys, separators=(",", ":"))
    return transform(s)
