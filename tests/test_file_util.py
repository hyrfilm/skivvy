import os
from pathlib import Path

import pytest

from skivvy.util.file_util import list_files, strip_filename, write_tmp, cleanup_tmp_files, _tmp_files


def _relative_paths(base: Path, files: list[str]) -> list[str]:
    return [Path(f).relative_to(base).as_posix() for f in files]


def test_list_files_uses_lexical_order_by_default(tmp_path):
    tests_dir = tmp_path / "tests"
    (tests_dir / "10_group").mkdir(parents=True)
    (tests_dir / "2_group").mkdir(parents=True)
    (tests_dir / "2_group" / "10_case.json").write_text("{}")
    (tests_dir / "2_group" / "2_case.json").write_text("{}")
    (tests_dir / "10_group" / "1_case.json").write_text("{}")

    files = list_files(str(tests_dir), ".json")

    assert _relative_paths(tmp_path, files) == [
        "tests/10_group/1_case.json",
        "tests/2_group/10_case.json",
        "tests/2_group/2_case.json",
    ]


def test_list_files_supports_natural_order(tmp_path):
    tests_dir = tmp_path / "tests"
    (tests_dir / "10_group").mkdir(parents=True)
    (tests_dir / "2_group").mkdir(parents=True)
    (tests_dir / "2_group" / "10_case.json").write_text("{}")
    (tests_dir / "2_group" / "2_case.json").write_text("{}")
    (tests_dir / "10_group" / "1_case.json").write_text("{}")

    files = list_files(str(tests_dir), ".json", file_order="natural")

    assert _relative_paths(tmp_path, files) == [
        "tests/2_group/2_case.json",
        "tests/2_group/10_case.json",
        "tests/10_group/1_case.json",
    ]


def test_list_files_rejects_unknown_file_order(tmp_path):
    with pytest.raises(ValueError, match="Unknown file_order"):
        list_files(str(tmp_path), ".json", file_order="weird")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("my_file", "my_file"),
        ("./my_file.png", "my_file.png"),
        ("some/path/here/my_file.png", "my_file.png"),
    ],
)
def test_strip_filename_returns_last_path_component(raw, expected):
    assert strip_filename(raw) == expected


def test_write_tmp_rejects_overwrite(tmp_path, monkeypatch, clean_tmp_files):
    monkeypatch.chdir(tmp_path)
    write_tmp("out.txt", "first")
    with pytest.raises(ValueError, match="already exists"):
        write_tmp("out.txt", "second")


def test_cleanup_tmp_files(tmp_path, monkeypatch, clean_tmp_files):
    monkeypatch.chdir(tmp_path)
    tmp_file = write_tmp("out.txt", "hello")
    missing_file = write_tmp("gone.txt", "where is it?")

    os.remove(missing_file)
    # should just result in a warning
    cleanup_tmp_files(warn=True, throw=False)

    tmp_file = write_tmp("out.txt", "hello")
    missing_file = write_tmp("gone.txt", "but it was right there!")
    also_missing = write_tmp("poof.txt", "like it never existed")
    os.remove(missing_file)
    os.remove(also_missing)

    try:
        cleanup_tmp_files(warn=False, throw=True)
    except ExceptionGroup as e:
        # two files should have resulted in errors when trying to remove
        assert len(e.exceptions) == 2

    # all files should be gone
    paths = [tmp_file, missing_file, missing_file]
    for path in paths:
        assert not os.path.isfile(path)
