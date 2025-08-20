import codecs
import json
import os

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


def cleanup_tmp_files():
    for filename in _tmp_files:
        os.remove(filename)


def read_file_contents(filename):
    with open(filename) as fp:
        return fp.read()

def set_current_file(filename):
    os.environ["SKIVVY_CURRENT_FILE"] = filename
    os.environ["SKIVVY_CURRENT_DIR"] = os.path.dirname(filename)

def split_all(path):
    allparts = []
    while True:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts