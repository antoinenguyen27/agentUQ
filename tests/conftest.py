import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent


def pytest_collection_modifyitems(config, items):
    run_live = os.getenv("AGENTUQ_RUN_LIVE") == "1"
    skip_live = pytest.mark.skip(reason="live tests are opt-in; set AGENTUQ_RUN_LIVE=1 and the required API keys to run them")
    for item in items:
        if "live" in item.keywords and not run_live:
            item.add_marker(skip_live)

