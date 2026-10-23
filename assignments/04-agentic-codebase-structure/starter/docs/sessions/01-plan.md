# Stage 1: Plan (no edits)

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `plan`

## Prompt

```text
Plan task 1 (Custom alias) from docs/TASKS.md. Inspect the task, the code, and the tests, then propose a plan: expected behavior, edge cases, tests to add, and files to change. Do not edit any files.
```

## Tool calls, in order

1. Agent
2. ScheduleWakeup
3. Bash: `BASE="~/Desktop/ÖDEVDOSYAM2027/AI-Augmented-Software-Engineering/assignments/04-agentic-codebase-structure/starter"; ls -la "$BASE"; echo "-…`
4. Read: `docs/TASKS.md`
5. Read: `main.py`
6. Read: `tests/test_main.py`
7. Read: `tests/AGENTS.md`
8. Read: `AGENTS.md`
9. Read: `.claude/skills/implement-feature/SKILL.md`
10. Read: `requirements.txt`
11. Read: `pytest.ini`
12. Agent
13. ScheduleWakeup
14. Bash: `ls -la && echo --- && cat docs/TASKS.md 2>/dev/null && echo --- && cat AGENTS.md 2>/dev/null && echo --- && cat tests/AGENTS.md 2>/dev/null`
15. Bash: `git status && echo --- && git log --oneline -10`
16. Bash: `find .claude -type f | xargs -I{} echo {} && echo --- && cat .claude/skills/implement-feature/*.md 2>/dev/null`
17. Read: `tests/test_main.py`
18. Read: `main.py`
19. ScheduleWakeup
20. Read: `main.py`
21. Read: `tests/test_main.py`
22. ToolSearch
23. ToolSearch
24. ToolSearch
25. ToolSearch
26. Write: `~/.claude/plans/plan-task-1-custom-purrfect-treasure.md`

## Agent's final answer

I've written the full plan to `~/.claude/plans/plan-task-1-custom-purrfect-treasure.md`. Summary:

**Behavior**: `ShortenRequest` gets an optional `alias: str | None = None`. If given and unused, it's inserted directly as `code` (skipping `encode()`); if already taken (by another alias *or* an existing auto-generated code — same `UNIQUE` column, no extra logic needed), return 409. Conflict detection relies on a single `INSERT` wrapped in `try/except sqlite3.IntegrityError` rather than check-then-insert, avoiding a race condition. Omitting `alias` leaves current behavior untouched.

**Files**: only `main.py` (`ShortenRequest` + `shorten()`) and `tests/test_main.py` (additive tests only, using a new `temp_db` fixture per `tests/AGENTS.md`'s monkeypatch rule — the 3 existing tests stay as-is).

**Tests to add**: alias success + redirect, alias conflicts with another alias → 409, alias conflicts with an auto-generated code → 409, omitting alias still works, and empty/whitespace alias → 400 (pending your call below).

**Flagged, not fixed**: once aliases exist, a *future* auto-generated code could coincidentally collide with an already-claimed alias, and that path has no conflict handling today — would 500 instead of a clean error. This is a new risk this task introduces; I'm recommending leaving it alone per the project's "smallest change" rule, but wanted you to see it rather than silently inherit it.

Two small decisions I'd like you to confirm before implementation:
1. Should an empty-string or whitespace-only `alias` be rejected with 400 (my recommendation — it would otherwise create an unreachable link), or accepted literally per the task's exact wording?
2. Should a provided alias be stored verbatim, or `.strip()`'d of surrounding whitespace before storing? I'd default to verbatim (smaller change).

Let me know your call on those two, or just say "go with your recommendation" and I'll proceed with both as written in the plan.

## Plan file the agent wrote

# Plan: Task 1 — Custom alias

## Context

`docs/TASKS.md` lists three independent features for the link shortener; this assignment
implements exactly one. Task 1's text, verbatim:

> **Custom alias** — allow `POST /shorten` to accept an optional `alias`; use it as the code
> if it is available, otherwise return 409.

Today, `POST /shorten` always derives the short code from the row's auto-increment id via
`encode()` (base62). This task lets a caller request a specific code instead. The `code`
column is already `TEXT UNIQUE`, so "available" naturally means "no existing row has this
code" — which SQLite already enforces for us.

## Expected behavior

`ShortenRequest` gains an optional field:

```python
class ShortenRequest(BaseModel):
    url: str
    alias: str | None = None
```

In `shorten()`:
- **`alias` omitted or `null`** → unchanged: auto-generate via `encode(row_id)` exactly as today.
- **`alias` provided and not already taken** → insert the row with `code = alias` directly
  (skip `encode()` entirely). Response shape is unchanged: `{"code": alias, "short_url": f"/{alias}"}`.
- **`alias` provided and already taken** (by another custom alias *or* by an existing
  auto-generated code — same `code` column, no special-casing needed) → `409`,
  `detail="alias already taken"`.
- **`alias` is `""` or whitespace-only** → `400`, `detail="alias must not be empty"`, checked
  before touching the DB. (See "Decision" below.)

Conflict detection: attempt `INSERT INTO links (url, code) VALUES (?, ?)` directly inside a
`try/except sqlite3.IntegrityError`, catching the existing `UNIQUE` constraint violation and
turning it into the 409. This is preferred over a `SELECT`-then-`INSERT` check, which has a
TOCTOU race between the check and the write; the single INSERT is atomic. `sqlite3` is already
imported in `main.py`, so no new import is needed.

URL validation keeps its current precedence: the `url` format check still runs first, so if
both `url` and `alias` are invalid, the existing 400 for `url` wins unchanged.

## Decision needed from you

1. **Empty/whitespace alias → 400, or accept literally?** `GET /{code}` can't match an empty
   path segment, so an alias of `""` would create a link nobody could ever reach. Recommended:
   reject with 400 (mirrors the existing `url` validation style). Confirm, or say to accept it
   literally per the task's exact wording.
2. **Leave the alias value as-is, or `.strip()` it before storing?** Recommended: store
   verbatim (only use `.strip()` for the emptiness *check*, not to mutate the value) — smaller
   change, doesn't silently rewrite user input.

I'll proceed with the recommended option for both unless you say otherwise.

## Edge cases covered by tests

| Case | Status |
| --- | --- |
| No `alias` (or explicit `null`) | 200, same as today |
| Alias provided, available | 200, `code` == alias |
| Alias collides with another custom alias | 409 |
| Alias collides with an existing auto-generated code | 409 |
| Alias is `""` / whitespace-only | 400 (pending decision #1) |

**Known, out-of-scope risk — flagged, not fixed:** once custom aliases exist, a *future*
auto-generated `encode(row_id)` could coincidentally collide with a previously-claimed custom
alias. The auto-generate path's `UPDATE ... SET code = ?` has no conflict handling today, so
that specific collision would surface as an unhandled `sqlite3.IntegrityError` → 500, not a
clean error. This is a new failure mode introduced by adding aliases (before this task,
`encode()` outputs were provably collision-free). Per `AGENTS.md`'s "smallest change" rule and
"ask before changing behavior beyond what's needed," I'm not fixing this as part of Task 1 —
flagging it here for your awareness, not asking you to decide it now.

**Known pre-existing limitation — not in scope:** `AGENTS.md` already documents that the single
`GET /{code}` catch-all shares URL space with FastAPI's `/docs`, `/redoc`, `/openapi.json`. An
alias like `"docs"` would create a link that's unreachable via GET (those built-in routes win
the match). Not something this task is asked to fix.

## Files to change

- **`main.py`** — only `ShortenRequest` (add `alias` field) and `shorten()` (branch logic
  above). `encode()`, `get_db()`, `init_db()`, `redirect()` stay untouched.
- **`tests/test_main.py`** — additive only; the 3 existing tests stay byte-for-byte unchanged.
  New tests need a temp-DB fixture per `tests/AGENTS.md` (the existing tests don't have one —
  pre-existing gap, out of scope to fix here). Add near the top:
  ```python
  import pytest
  import main  # needed to monkeypatch main.DB_PATH and call main.init_db()

  @pytest.fixture()
  def temp_db(monkeypatch, tmp_path):
      monkeypatch.setattr(main, "DB_PATH", tmp_path / "links.db")
      main.init_db()
  ```

## Tests to add

All take `temp_db` as a fixture parameter; all assert status codes (and response/location where
relevant), matching the existing file's style of not asserting exact `detail` text:

1. `test_custom_alias_used_as_code_and_redirects(temp_db)` — `POST /shorten` with
   `{"url": "https://example.com", "alias": "mylink"}` → 200,
   `{"code": "mylink", "short_url": "/mylink"}`; then `GET /mylink` → 307 to
   `https://example.com`.
2. `test_alias_already_taken_by_custom_alias_returns_409(temp_db)` — claim `alias="dup"`, then
   claim it again with a different `url` → 409.
3. `test_alias_already_taken_by_auto_generated_code_returns_409(temp_db)` — shorten with no
   alias, capture the returned `code`, then shorten again using that code as the `alias` → 409.
   This specifically proves the single UNIQUE-constraint check catches cross-origin collisions.
4. `test_omitting_alias_preserves_auto_generate_behavior(temp_db)` — `POST /shorten` with only
   `{"url": ...}` → 200, non-empty `code`; `GET /{code}` → 307 with correct `location`
   (regression guard under the new fixture).
5. `test_empty_string_alias_returns_400(temp_db)` and
   `test_whitespace_only_alias_returns_400(temp_db)` — only if decision #1 confirms rejecting
   empty/whitespace aliases.

## Verification

```bash
pytest tests/test_main.py -v   # iterate on this file alone first
pytest                          # full suite before considering this done
```
All 3 existing tests plus the ~5–6 new ones must pass.

