import sys

from skivvy.skivvy import run
from skivvy.util import file_util


# TODO: This a ugly and slow and bad and hacky since we're hitting the actual end-points but blabla fix laterrrz

def test_jsonplaceholder_examples():
    cfg_file = "examples/typicode/default.json"
    result = run_examples(cfg_file)
    assert result, f"Example config {cfg_file} failed"

def test_dummyjson_examples():
    cfg_file = "examples/dummyjson/dummy.json"
    result = run_examples(cfg_file)
    assert result, f"Example config {cfg_file} failed"
    # god knows why this is needed
    file_util.cleanup_tmp_files(throw=False)


def run_examples(cfg_file):
    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", "-t", str(cfg_file)]
        result = run()
    finally:
        sys.argv = old_argv
    return result
