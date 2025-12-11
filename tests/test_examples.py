import sys

from skivvy.skivvy import run


def test_jsonplaceholder_examples():
    cfg_file = "examples/typicode/default.json"
    result = run_examples(cfg_file)
    assert result, f"Example config {cfg_file} failed with result={result!r}"

def test_jsonplaceholder_examples():
    cfg_file = "examples/dummyjson/dummy.json"
    result = run_examples(cfg_file)
    assert result, f"Example config {cfg_file} failed with result={result!r}"



def run_examples(cfg_file):
    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", "-t", str(cfg_file)]
        result = run()
    finally:
        sys.argv = old_argv
    return result
