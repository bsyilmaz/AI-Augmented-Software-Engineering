# Stage 2: Implement with the implement-feature skill

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `acceptEdits`

## Prompt

```text
/implement-feature 1 (Custom alias). Use the plan in docs/sessions/01-plan.md together with the human decisions in docs/sessions/02-plan-decisions.md: reject empty or whitespace-only aliases with 400, store aliases verbatim, make auto-generated codes never fail when an alias already holds that code, and reject unreachable aliases (containing '/', or equal to docs, redoc, or openapi.json) with 400.
```

## Tool calls, in order

1. Read: `docs/TASKS.md`
2. Read: `tests/AGENTS.md`
3. Read: `docs/sessions/01-plan.md`
4. Read: `docs/sessions/02-plan-decisions.md`
5. Read: `main.py`
6. Read: `tests/test_main.py`
7. Read: `requirements.txt`
8. Edit: `tests/test_main.py`
9. Bash: `pytest tests/test_main.py -v 2>&1 | tail -80`
10. Edit: `main.py`
11. Bash: `pytest -v 2>&1 | tail -40`

## Agent's final answer

All 14 tests pass.

```text
Behavior: POST /shorten accepts an optional alias. A valid, available alias is stored verbatim as the code (200, {"code": alias, "short_url": f"/{alias}"}); omitting alias keeps today's auto-generate behavior, but it now retries with a numeric suffix (e.g. "b2", "b3", ...) if encode(row_id) collides with an alias already in use, so it can never fail with a 500. An empty or whitespace-only alias returns 400. An alias containing "/" or equal to "docs", "redoc", or "openapi.json" returns 400 (unreachable). An alias already taken — by another alias or an existing auto-generated code — returns 409. url validation still runs first and is unchanged.

Files:
- main.py — added alias field to ShortenRequest, alias validation (empty/whitespace, unreachable names), direct INSERT with code=alias caught for 409 on conflict, and a retry loop on the auto-generate UPDATE to resolve collisions with taken aliases.
- tests/test_main.py — added a temp_db fixture (monkeypatch main.DB_PATH + main.init_db(), per tests/AGENTS.md) and 11 new tests covering: alias success + redirect, alias conflict with another alias, alias conflict with an auto-generated code, empty/whitespace alias, "/"-containing and reserved-name aliases (parametrized), the omit-alias regression, and the auto-generate collision recovery.

Tests: 14 added/kept, pytest → 14 passed.

Remaining risks: none flagged by the plan were left open — all four human decisions in docs/sessions/02-plan-decisions.md are implemented. One implementation detail not specified by the plan: the collision-recovery scheme for auto-generated codes appends a numeric suffix (base_code + "2", "3", ...) rather than some other strategy; this is an internal detail not asserted by tests beyond "it doesn't collide and doesn't fail."
```
