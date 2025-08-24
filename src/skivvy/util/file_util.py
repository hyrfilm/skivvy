import codecs
import json
import os
import pathlib

from skivvy.util import log

_tmp_files = []

def list_files(path, include_ext):
    result = []
    for root, subdirs, files in os.walk(path):
        subdirs.sort()
        for filename in sorted(files):
            if filename.endswith(include_ext):
                result.append(os.path.join(root, filename))

    return result


def parse_json(filename):
    with codecs.open(filename, 'r', encoding='utf8') as f:
        return json.load(f)


def write_tmp(filename, content):
    with open(filename, "w") as fp:
        fp.write(str(content))
        _tmp_files.append(filename)


def cleanup_tmp_files(warn: bool = False, throw: bool = True) -> None:
    missing = []
    for filename in _tmp_files:
        try:
            os.remove(filename)
        except FileNotFoundError as e:
            if warn: log.warn(f"Missing temporary file: {filename}")
            if throw: missing.append(e)
    if missing:
        raise ExceptionGroup("Missing file(s) when cleaning up:", missing)
        

def read_file_contents(filename):
    with open(filename) as fp:
        return fp.read()

# TODO: Move to something like an environment kind of file
def set_current_file(filename):
    os.environ["SKIVVY_CURRENT_FILE"] = filename
    os.environ["SKIVVY_CURRENT_DIR"] = pathlib.Path(filename).parent.parts[-1]
