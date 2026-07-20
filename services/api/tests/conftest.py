from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from codex_aware import app as app_module
from codex_aware.store import Store


@pytest.fixture()
def client(tmp_path, monkeypatch):
    test_store = Store(str(tmp_path / "aware.db"))
    monkeypatch.setattr(app_module, "store", test_store)
    # These unit tests exercise the HTTP contract without repeatedly starting
    # the process-scoped MCP session manager.
    yield TestClient(app_module.app)
