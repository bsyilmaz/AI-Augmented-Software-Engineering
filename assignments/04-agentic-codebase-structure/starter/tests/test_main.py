import pytest
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "links.db")
    main.init_db()


def test_shorten_and_redirect():
    r = client.post("/shorten", json={"url": "https://example.com"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code
    r2 = client.get(f"/{code}", follow_redirects=False)
    assert r2.status_code == 307
    assert r2.headers["location"] == "https://example.com"


def test_rejects_bad_url():
    r = client.post("/shorten", json={"url": "ftp://nope"})
    assert r.status_code == 400


def test_unknown_code_404():
    r = client.get("/does-not-exist", follow_redirects=False)
    assert r.status_code == 404


def test_custom_alias_used_as_code_and_redirects(temp_db):
    r = client.post("/shorten", json={"url": "https://example.com", "alias": "mylink"})
    assert r.status_code == 200
    assert r.json() == {"code": "mylink", "short_url": "/mylink"}
    r2 = client.get("/mylink", follow_redirects=False)
    assert r2.status_code == 307
    assert r2.headers["location"] == "https://example.com"


def test_omitting_alias_preserves_auto_generate_behavior(temp_db):
    r = client.post("/shorten", json={"url": "https://example.com"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code
    r2 = client.get(f"/{code}", follow_redirects=False)
    assert r2.status_code == 307
    assert r2.headers["location"] == "https://example.com"


def test_alias_already_taken_by_custom_alias_returns_409(temp_db):
    r1 = client.post("/shorten", json={"url": "https://example.com", "alias": "dup"})
    assert r1.status_code == 200
    r2 = client.post("/shorten", json={"url": "https://other.example", "alias": "dup"})
    assert r2.status_code == 409


def test_alias_already_taken_by_auto_generated_code_returns_409(temp_db):
    r1 = client.post("/shorten", json={"url": "https://example.com"})
    assert r1.status_code == 200
    taken_code = r1.json()["code"]
    r2 = client.post("/shorten", json={"url": "https://other.example", "alias": taken_code})
    assert r2.status_code == 409


def test_empty_string_alias_returns_400(temp_db):
    r = client.post("/shorten", json={"url": "https://example.com", "alias": ""})
    assert r.status_code == 400


def test_whitespace_only_alias_returns_400(temp_db):
    r = client.post("/shorten", json={"url": "https://example.com", "alias": "   "})
    assert r.status_code == 400


@pytest.mark.parametrize(
    "alias",
    ["a/b", "docs", "redoc", "openapi.json"],
)
def test_unreachable_alias_returns_400(temp_db, alias):
    r = client.post("/shorten", json={"url": "https://example.com", "alias": alias})
    assert r.status_code == 400


def test_auto_generated_code_never_fails_when_alias_already_holds_that_code(temp_db):
    # The next auto-generated code (row id 1) would be encode(1) == "b"; claim it as
    # an alias first, then force the auto-generate path to collide and recover.
    claim = client.post("/shorten", json={"url": "https://claimed.example", "alias": "b"})
    assert claim.status_code == 200

    r = client.post("/shorten", json={"url": "https://example.com"})
    assert r.status_code == 200
    code = r.json()["code"]
    assert code != "b"

    r2 = client.get(f"/{code}", follow_redirects=False)
    assert r2.status_code == 307
    assert r2.headers["location"] == "https://example.com"
