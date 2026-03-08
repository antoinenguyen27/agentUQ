from __future__ import annotations

import os

import pytest


def require_live_env(*env_vars: str) -> None:
    if os.getenv("AGENTUQ_RUN_LIVE") != "1":
        pytest.skip("Set AGENTUQ_RUN_LIVE=1 to run live provider/framework smoke tests.")
    missing = [name for name in env_vars if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing required live-test environment variables: {', '.join(missing)}")


def assert_live_result(result) -> None:
    assert result.capability_level.value != "none"
    assert result.decision is not None
    assert result.segments or result.events

