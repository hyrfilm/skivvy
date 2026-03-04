import codecs
import json
import os
import pathlib
import re

from skivvy.util import log

_tmp_files = set()
_natural_sort_re = re.compile(r"(\d+)")


def _natural_sort_key(value: str):
    parts = _natural_sort_re.split(value)
    key = []
    for part in parts:
        if part.isdigit():
            key.append((0, int(part), part))
        else:
            key.append((1, part.casefold(), part))
    return tuple(key)


def _sort_key(file_order: str):
    if file_order == "lexical":
        return None
    if file_order == "natural":
        return _natural_sort_key
    raise ValueError(
        f'Unknown file_order "{file_order}". Supported values: lexical, natural'
    )


def list_files(path, include_ext, file_order="lexical"):
    key = _sort_key(file_order)
    result = []
    for root, subdirs, files in os.walk(path):
        subdirs.sort(key=key)
        for filename in sorted(files, key=key):
            if filename.endswith(include_ext):
                result.append(os.path.join(root, filename))

    return result


def parse_json(filename):
    with open(filename, "r", encoding="utf8") as f:
        return json.load(f)


def write_tmp(filename, content):
    filename = os.path.join(os.getcwd(), filename)
    if filename in _tmp_files:
        raise ValueError(f"Temporary file already exists: {filename}")
    with open(filename, "w") as fp:
        fp.write(str(content))
    _tmp_files.add(filename)
    return filename


def cleanup_tmp_files(warn: bool = False, throw: bool = True) -> None:
    missing = []
    while len(_tmp_files) > 0:
        filename = _tmp_files.pop()
        try:
            os.remove(filename)
        except FileNotFoundError as e:
            if warn:
                log.warning(f"Missing temporary file: {filename}")
            if throw:
                missing.append(e)
    if missing:
        raise ExceptionGroup("Missing file(s) when cleaning up:", missing)

def read_file_contents(filename, binary: bool = False):
    mode = "rb" if binary else "r"
    kwargs = {} if binary else {"encoding": "utf8"}
    with open(filename, mode, **kwargs) as fp:
        return fp.read()


def strip_filename(filename: str) -> str:
    return os.path.basename(filename)


# TODO: Move to something like an environment kind of file
def set_current_file(filename):
    os.environ["SKIVVY_CURRENT_FILE"] = filename
    os.environ["SKIVVY_CURRENT_DIR"] = pathlib.Path(filename).parent.parts[-1]
