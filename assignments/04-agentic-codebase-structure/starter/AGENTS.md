# Agent guide: Link Shortener

A tiny FastAPI + SQLite service. `POST /shorten` stores a URL and returns a short code;
`GET /{code}` redirects to the stored URL with HTTP 307.

## Where things are

| Path | What it holds |
| --- | --- |
| `main.py` | The whole app: SQLite setup, base62 `encode()`, request model, both routes |
| `tests/test_main.py` | Behavioral tests through FastAPI's `TestClient` |
| `tests/AGENTS.md` | Rules for writing tests (loads when you work in `tests/`) |
| `docs/TASKS.md` | The three feature tasks; implement only the one you are given |
| `.claude/skills/implement-feature/` | Step-by-step procedure for a feature task |
| `links.db` | Local SQLite file created at import time; never commit it |

## Commands

Run from this directory with the virtual environment active:

```bash
pip install -r requirements.txt   # install
pytest                            # run all tests (pytest.ini points at tests/)
uvicorn main:app --reload         # run at http://localhost:8000 (docs at /docs)
```

## Product boundaries

In scope: shortening `http://` and `https://` URLs, redirecting by code, and the feature in
`docs/TASKS.md` you were asked to build.

Out of scope unless a person asks: user accounts or authentication, a web UI, analytics beyond
the assigned task, rate limiting, a different database, new dependencies, and the other tasks
in `docs/TASKS.md`.

## How the code behaves today

- Codes are base62 strings made from the row id (`encode(row_id)`), stored in the `code` column,
  which is `UNIQUE`.
- Errors use `HTTPException` with a short `detail` string: 400 for a bad URL, 404 for an unknown code.
- The app has a single `GET /{code}` catch-all, so FastAPI's own `/docs`, `/redoc`, and
  `/openapi.json` paths share the same URL space as short codes.

## Change workflow

1. **Understand**: read the task, `main.py`, and the related tests. State the expected behavior.
2. **Test**: add a failing behavioral test for the success case and at least one failure case.
3. **Implement**: make the smallest change in `main.py` that passes the tests.
4. **Verify**: run `pytest`; all old and new tests must pass before you stop.

For a feature task, follow the `implement-feature` skill. Ask a person before adding a
dependency, changing the database schema beyond what the task needs, or deleting tests.
