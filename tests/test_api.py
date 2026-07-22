"""API wiring tests. /health needs no network. Run: pip install -e ".[test]" && python tests/test_api.py"""

from fastapi.testclient import TestClient

from voiceagent.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_routes_registered():
    paths = {route.path for route in app.routes}
    assert {"/health", "/ask", "/describe", "/ingest"} <= paths


if __name__ == "__main__":
    test_health()
    test_routes_registered()
    print("✓ api wiring tests passed")
