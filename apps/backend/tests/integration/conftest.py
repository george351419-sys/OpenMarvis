import os

import pytest

# v1.0 起统一用 OPENMARVIS_LIVE；保留 OPENMARVIS_M2_LIVE 作为 deprecated alias。
LIVE = (
    os.environ.get("OPENMARVIS_LIVE") == "1"
    or os.environ.get("OPENMARVIS_M2_LIVE") == "1"
)


def pytest_collection_modifyitems(items):
    if LIVE:
        return
    skip = pytest.mark.skip(reason="set OPENMARVIS_LIVE=1 to enable")
    for item in items:
        # Only skip tests from the integration directory
        if "tests/integration" in str(item.fspath):
            item.add_marker(skip)
