"""Shared pytest fixtures/config for the app test suite.

Makes the app/ directory importable (so `import agent_utils` works when running
from app/) and keeps the suite offline by default: tests that need live
Bedrock/AWS are marked @pytest.mark.live and are skipped unless --run-live is
passed.
"""

import os
import sys

import pytest

# Put the app/ directory (parent of tests/) on sys.path so `import agent_utils`
# resolves regardless of the working directory pytest was launched from.
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.live (calls real Bedrock/AWS).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: test requires live Bedrock/AWS; skipped offline unless --run-live.",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-live"):
        return
    skip_live = pytest.mark.skip(reason="needs live Bedrock/AWS (pass --run-live to enable)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
