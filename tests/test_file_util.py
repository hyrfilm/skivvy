from pathlib import Path

import pytest

from skivvy.util.file_util import list_files, strip_filename


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
