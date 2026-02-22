import uuid

import pytest

from skivvy import matchers
from skivvy.util import file_util, scope


@pytest.fixture
def isolated_matcher_state(monkeypatch):
    # Matchers mutate global module state (registry + options), so tests that
    # exercise matcher registration should run against a per-test snapshot.
    monkeypatch.setattr(matchers, "matcher_dict", dict(matchers.matcher_dict))
    monkeypatch.setattr(matchers, "_matcher_options", dict(matchers._matcher_options))
    yield


@pytest.fixture
def isolated_scope_namespace(monkeypatch):
    namespace = f"pytest-{uuid.uuid4().hex}"
    monkeypatch.setenv("SKIVVY_CURRENT_DIR", namespace)
    yield namespace
    scope._store.pop(namespace, None)
    scope.set_validate_variable_names(True)


@pytest.fixture
def clean_tmp_files():
    file_util._tmp_files.clear()
    yield
    file_util.cleanup_tmp_files(warn=False, throw=False)
    file_util._tmp_files.clear()
