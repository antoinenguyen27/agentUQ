from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests.live.helpers import require_live_env


def _load_collection_hook():
    conftest_path = Path(__file__).resolve().parents[1] / "conftest.py"
    spec = importlib.util.spec_from_file_location("agentuq_tests_conftest", conftest_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.pytest_collection_modifyitems


class _FakeItem:
    def __init__(self, *, live: bool):
        self.keywords = {"live": True} if live else {}
        self.markers = []

    def add_marker(self, marker):
        self.markers.append(marker)


def test_require_live_env_skips_when_flag_missing(monkeypatch):
    monkeypatch.delenv("AGENTUQ_RUN_LIVE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(pytest.skip.Exception, match="AGENTUQ_RUN_LIVE=1"):
        require_live_env("OPENAI_API_KEY")


def test_require_live_env_skips_when_provider_key_missing(monkeypatch):
    monkeypatch.setenv("AGENTUQ_RUN_LIVE", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(pytest.skip.Exception, match="OPENAI_API_KEY"):
        require_live_env("OPENAI_API_KEY")


def test_require_live_env_returns_when_all_requirements_are_present(monkeypatch):
    monkeypatch.setenv("AGENTUQ_RUN_LIVE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    require_live_env("OPENAI_API_KEY")


def test_collection_hook_marks_live_tests_skipped_when_flag_missing(monkeypatch):
    monkeypatch.delenv("AGENTUQ_RUN_LIVE", raising=False)
    hook = _load_collection_hook()
    live_item = _FakeItem(live=True)
    normal_item = _FakeItem(live=False)

    hook(config=None, items=[live_item, normal_item])

    assert len(live_item.markers) == 1
    assert not normal_item.markers


def test_collection_hook_leaves_live_tests_unmodified_when_flag_enabled(monkeypatch):
    monkeypatch.setenv("AGENTUQ_RUN_LIVE", "1")
    hook = _load_collection_hook()
    live_item = _FakeItem(live=True)

    hook(config=None, items=[live_item])

    assert not live_item.markers

