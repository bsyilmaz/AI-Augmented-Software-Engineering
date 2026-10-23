# Stage 5: Re-review (no edits)

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `plan`

## Prompt

```text
Review the custom alias change (task 1 in docs/TASKS.md) again without editing any files. The previous review is in docs/sessions/04-review.md and the fixes are in the latest commit. Inspect 'git diff 9ec7bb2 HEAD -- main.py tests/', AGENTS.md, tests/AGENTS.md, and docs/sessions/02-plan-decisions.md. Check correctness, edge cases, test quality, and scope, and confirm the earlier findings are resolved. Run pytest. End with exactly one verdict line, ACCEPT or REVISE, followed by a short explanation.
```

## Tool calls, in order

1. Agent
2. Read: `docs/sessions/04-review.md`
3. Read: `docs/sessions/02-plan-decisions.md`
4. Read: `docs/TASKS.md`
5. Read: `tests/AGENTS.md`
6. Read: `main.py`
7. Read: `tests/test_main.py`
8. Bash: `git diff 9ec7bb2 HEAD -- main.py tests/`
9. Bash: `git log --oneline 9ec7bb2..HEAD`
10. Bash: `ls -la | grep -i venv; ls -la .venv 2>&1 | head -5`
11. Bash: `source .venv/bin/activate 2>/dev/null; which pytest python3; pytest -v 2>&1 || python3 -m pytest -v 2>&1`
12. Write: `~/.claude/plans/review-the-custom-alias-bright-goose.md`
13. ToolSearch
14. ExitPlanMode

## Agent's final answer

ACCEPT — The fix in `c9db448` correctly resolves the prior REVISE finding: `test_auto_generated_code_recovers_from_collision_with_claimed_alias` now learns the next natural code via two probe `POST /shorten` calls (never assumes it), claims that exact code as an alias in a fresh db, then issues a plain `POST /shorten` that genuinely collides and must take the suffix-retry path — traced by hand against `main.py`, this test would fail if the retry loop were reverted, unlike the vacuous original. The same commit also moved the three original tests onto the `temp_db` fixture, cleaning up the prior review's secondary non-blocking note about writing to the real `links.db`. All four decisions in `docs/sessions/02-plan-decisions.md` remain correctly implemented and now fully tested; validation order and `UNIQUE`/`IntegrityError` handling are correct on both the alias and auto-generate paths; tests follow `tests/AGENTS.md` (public API only, behavior-only assertions, independent, named after behavior); scope stayed within task 1. `pytest -v`: 14 passed, 0 failed (1 unrelated `httpx`/`starlette` deprecation warning). No files were edited for this review.

## Plan file the agent wrote

# Review: custom alias feature (task 1) — re-review after fix

## Context

This is a second, read-only review of the custom-alias change on branch `week4-bsyilmaz`
(commits `9ec7bb2..HEAD`), requested after a prior review (`docs/sessions/04-review.md`)
returned REVISE over one vacuous test. The fix is in commit `c9db448`. The task here is
purely to verify the fix resolved the finding and nothing regressed — there is no
implementation to plan, so this file records the review conclusion rather than a build plan.

## What was inspected

- `docs/sessions/04-review.md` (prior review and its one finding)
- `docs/sessions/02-plan-decisions.md` (4 recorded decisions)
- `docs/TASKS.md` task 1, root `AGENTS.md`, `tests/AGENTS.md`
- `git diff 9ec7bb2 HEAD -- main.py tests/` (cumulative diff)
- Full `main.py` and `tests/test_main.py` at HEAD
- `pytest -v`: 14 passed, 0 failed

## Prior finding and its resolution

**Prior finding (REVISE):** `test_auto_generated_code_never_fails_when_alias_already_holds_that_code`
assumed claiming alias `"b"` would force the next plain `POST /shorten` to collide at
`encode(1)`, but claiming the alias itself consumes row id 1, so the next plain insert got
row id 2 (`encode(2) == "c"`), never colliding — the retry/suffix branch was never exercised.

**Fix (`c9db448`):** replaced it with
`test_auto_generated_code_recovers_from_collision_with_claimed_alias`, which:
1. In a throwaway probe db, issues two plain `POST /shorten` calls and reads the second
   response's code (`next_natural_code`) — learned from the public API, not assumed.
2. In a fresh db, claims `next_natural_code` as an alias first (consuming row id 1).
3. Issues one plain `POST /shorten` (gets row id 2, whose `base_code == next_natural_code`,
   forcing the `IntegrityError` → suffix retry in `main.py`).
4. Asserts the returned code differs from `next_natural_code` and still redirects correctly.

Traced by hand against `main.py`'s logic: this correctly forces and observes the retry path
(reverting the retry loop to the original two-liner would now fail this test). It satisfies
`tests/AGENTS.md`'s "do not assume which code the next `POST /shorten` returns" and does not
call `encode()`/SQL directly. The same commit also moved the three original tests onto the
`temp_db` fixture, resolving the prior review's secondary (non-blocking) note about writing
to the real `links.db`.

## Decision-by-decision compliance (all 4, from `02-plan-decisions.md`)

1. Empty/whitespace alias → 400 — implemented and tested (`test_empty_string_alias_returns_400`,
   `test_whitespace_only_alias_returns_400`).
2. Store alias unstripped — implemented (`.strip()` used only for the truthiness check).
3. Auto-generated code colliding with a claimed alias — implemented via retry/suffix loop,
   now correctly covered by the fixed test above.
4. Unreachable aliases (containing `/`, or `docs`/`redoc`/`openapi.json`) → 400 — implemented
   via `UNREACHABLE_ALIASES` and tested with a parametrized case for each.

## Other checks — no issues found

- Correctness: URL validation before alias validation, atomic `UNIQUE`/`IntegrityError`
  handling for both the alias-insert and the auto-generate/retry paths, no SELECT-then-INSERT
  race, connection cleanup via `closing()` on every path.
- Test quality: all tests use `TestClient` + fixtures only, assert on status codes/JSON/
  `location` header (no internals), independent of each other and of execution order, named
  after behavior.
- Scope: only `main.py`/`tests/` touched; no new dependency; no schema change beyond what
  task 1 needs; no tests deleted; error style (`HTTPException` + short `detail`; 400/409)
  matches existing conventions and the task's explicit 409 requirement.
- `pytest -v`: **14 passed, 0 failed** (1 unrelated `httpx`/`starlette` deprecation warning).

## Verdict

**ACCEPT** — The fix in `c9db448` correctly resolves the prior REVISE finding: the
collision-recovery test now derives the colliding code from the public API and genuinely
forces and observes the retry/suffix path (confirmed by tracing `main.py`'s logic by hand),
and the secondary non-blocking note about the original three tests writing to the real
`links.db` was also cleaned up. All four decisions from `02-plan-decisions.md` are
implemented and tested, scope stayed within task 1, and all 14 tests pass. No further changes
needed.

