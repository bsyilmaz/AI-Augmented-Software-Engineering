# Test rules

These rules apply when you read or write files in `tests/`. They are not needed for
application-only work, so they live here instead of in the root `AGENTS.md`.

- **Test through the public API.** Use `fastapi.testclient.TestClient` and HTTP calls
  (`client.post("/shorten", ...)`, `client.get(f"/{code}", follow_redirects=False)`).
  Do not call `encode()`, `get_db()`, or SQL directly from a test.
- **Cover success and failure.** Every behavior change needs at least one success test and one
  failure or edge-case test, for example a conflict, an invalid input, or an unknown code.
- **Keep tests independent.** Each test must pass alone and in any order. Do not rely on a
  code created by another test, and do not assume which code the next `POST /shorten` returns.
  Tests must not write to the real `links.db`; point the app at a temporary database in a
  fixture (for example, `monkeypatch` `main.DB_PATH` to a file under `tmp_path` and call
  `main.init_db()`).
- **Assert behavior, not internals.** Check status codes, response JSON, and the `location`
  header of redirects. Do not assert on row ids, table contents, or private helpers.
- **Name tests after behavior**, for example `test_alias_already_taken_returns_409`.

Run a single file while iterating with `pytest tests/test_main.py`, then the full `pytest`.
