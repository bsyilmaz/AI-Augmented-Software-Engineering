# Stage 3: Review (no edits)

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `plan`

## Prompt

```text
Review the custom alias change (task 1 in docs/TASKS.md) without editing any files. Inspect the diff with 'git diff 9ec7bb2 HEAD -- main.py tests/', the task, AGENTS.md, tests/AGENTS.md, and the decisions in docs/sessions/02-plan-decisions.md. Check correctness, edge cases, test quality, and scope. Run pytest. End with exactly one verdict line, ACCEPT or REVISE, followed by a short explanation and, for REVISE, the specific findings.
```

## Tool calls, in order

1. Agent
2. Bash: `git diff 9ec7bb2 HEAD -- main.py tests/`
3. Bash: `AGENTS.md"`
4. Read: `docs/TASKS.md`
5. Read: `tests/AGENTS.md`
6. Read: `docs/sessions/02-plan-decisions.md`
7. Read: `main.py`
8. Read: `tests/test_main.py`
9. Bash: `.claude/skills/implement-feature/" 2>&1`
10. Bash: `ls -la | grep -i venv; ls -la .venv 2>&1 | head -5; ls -la venv 2>&1 | head -5`
11. Read: `.claude/skills/implement-feature/SKILL.md`
12. Bash: `source .venv/bin/activate 2>/dev/null; which python; python -m pytest -v 2>&1`
13. Bash: `source .venv/bin/activate 2>/dev/null; python3 -c "`
14. Bash: `source .venv/bin/activate 2>/dev/null; python3 -c "`
15. Write: `~/.claude/plans/review-the-custom-alias-playful-reef.md`
16. ToolSearch
17. ToolSearch
18. ExitPlanMode

## Agent's final answer

**REVISE**

Implementation of the custom-alias feature (task 1) is correct, well-scoped, and the new tests follow `tests/AGENTS.md` (public API only, `temp_db` fixture, success + failure coverage). All 14 tests pass. But one regression test is vacuous and should be fixed first.

**Finding:** `test_auto_generated_code_never_fails_when_alias_already_holds_that_code` doesn't exercise what it claims to. It claims alias `"b"` first, reasoning in its own comment that "the next auto-generated code (row id 1) would be `encode(1) == "b"`." That's wrong — claiming the alias itself consumes row id 1 (SQLite `AUTOINCREMENT` never reuses ids), so the following plain `POST /shorten` actually gets row id 2, whose natural code is `encode(2) == "c"`, which was never claimed. No collision occurs, so the retry/suffix branch is never entered. I verified this empirically against the real `main.py`: claiming `"b"` then posting plain returns `"c"` (test's assertion passes trivially either way); claiming `"c"` instead — which *is* `encode(2)` — and posting plain correctly returns `"c2"`, proving the retry logic only fires with the right setup. Net effect: decision #3 from `docs/sessions/02-plan-decisions.md` ("a future auto-generated code colliding with an existing alias... is part of the task") currently has **no regression coverage** — reverting the retry loop to the original two-liner would not fail any test. It also brushes against `tests/AGENTS.md`'s explicit rule against assuming which code the next `POST /shorten` returns.

Suggested fix shape (without calling `encode()` directly, since the test rules forbid that): derive the colliding alias from the public API — learn what two consecutive plain `POST /shorten` calls return in one fresh db, then in a second fresh db claim the second of those values as an alias before issuing one plain `POST /shorten`, and assert the result differs and still redirects.

Everything else is solid: correctness (validation order, atomic `UNIQUE`/`IntegrityError` handling, no race), decisions #1/#2/#4 correctly implemented and tested, scope stayed to task 1 (no new dependency, no schema change, no deleted tests), and error style matches existing conventions. One unrelated, pre-existing note: the three original tests still write to the real `links.db` instead of using `temp_db`, which `tests/AGENTS.md` now prohibits — not introduced by this diff, worth a separate cleanup.

No files were edited.

## Plan file the agent wrote

# Review: custom alias feature (task 1)

## Context

This is a review of the custom-alias change implemented between commits `9ec7bb2` and `HEAD`
on branch `week4-bsyilmaz`, against `docs/TASKS.md` task 1, the root `AGENTS.md`,
`tests/AGENTS.md`, and the recorded decisions in `docs/sessions/02-plan-decisions.md`. The
request was a read-only review producing an ACCEPT/REVISE verdict — no files were edited.

## What was inspected

- `git diff 9ec7bb2 HEAD -- main.py tests/`
- `docs/TASKS.md` (task 1 spec), root `AGENTS.md`, `tests/AGENTS.md`
- `docs/sessions/02-plan-decisions.md` (4 recorded decisions)
- Full `main.py` and `tests/test_main.py` at HEAD
- `pytest` run (14 passed)
- Empirical verification script run against the real `main.py`/`encode()` to trace exact
  row-id → code assignment for the collision-recovery test (see Finding 1)

## Decision-by-decision compliance

1. Empty/whitespace alias → 400: implemented (`if not req.alias.strip(): raise 400`). ✓.
2. Store alias unstripped: implemented — `req.alias` is inserted as-is, `.strip()` only used
   for the truthiness check. ✓ (no dedicated test for this specific behavior, minor).
3. Future auto-generated code colliding with an existing alias — fix in this task: a
   while/retry loop with an incrementing suffix was added around the `UPDATE ... code = ?`
   call. Implementation is correct (verified empirically). **However, the test meant to cover
   this is vacuous — see Finding 1.**
4. Unreachable aliases (`/` and `docs`/`redoc`/`openapi.json`) → 400: implemented via
   `UNREACHABLE_ALIASES` set and a `"/" in req.alias` check, and covered by a parametrized
   test over all four cases. ✓.

## Finding 1 (REVISE): the auto-generate collision test never exercises the retry logic

`test_auto_generated_code_never_fails_when_alias_already_holds_that_code` claims alias `"b"`
first, reasoning (per its own comment) that "the next auto-generated code (row id 1) would be
`encode(1) == "b"`". That reasoning ignores that claiming the alias itself consumes row id 1
(SQLite `AUTOINCREMENT` never reuses ids). The following plain `POST /shorten` therefore gets
row id **2**, whose natural code is `encode(2) == "c"` — which was never claimed, so no
collision happens and the retry/suffix branch in `main.py` is never entered.

Verified empirically (ran the real `main.py` against a temp db):
- Claiming alias `"b"` then posting with no alias → returns `"c"` (no collision, retry path
  skipped). The test's assertion `code != "b"` passes trivially either way.
- Claiming alias `"c"` instead (which *is* `encode(2)`, the id the next plain insert will
  actually get) then posting with no alias → returns `"c2"`, correctly showing the retry loop
  firing.

So decision #3 — explicitly called "part of the task" in the decisions doc — currently has
**no regression coverage**: reverting the retry loop back to the original two-line
`code = encode(row_id)` would not fail any test in the suite.

This also brushes against `tests/AGENTS.md`'s rule "do not assume which code the next
`POST /shorten` returns" — the test's premise is exactly that kind of assumption, and it's
wrong for this call sequence.

**Fix shape** (not prescribing exact code, since `tests/AGENTS.md` forbids calling `encode()`
directly from a test): derive the colliding value from the public API instead of a hardcoded
literal — e.g. use a probe sequence in a fresh db to learn what two consecutive plain
`POST /shorten` calls return, then in a second fresh db claim the second of those values as an
alias before issuing one plain `POST /shorten`, and assert the returned code differs and still
redirects correctly.

## Everything else checked — no other blocking issues

- Correctness: URL-first validation, alias validation ordering, atomicity via SQLite's
  `UNIQUE` constraint + `IntegrityError` handling (no SELECT-then-INSERT race), connection
  cleanup on the error path — all fine.
- Test quality otherwise: new tests use `TestClient` + `temp_db` fixture
  (`monkeypatch` on `main.DB_PATH` + `main.init_db()`), exactly as `tests/AGENTS.md`
  prescribes; no direct calls to `encode()`/`get_db()`/SQL; success and failure cases for
  every new behavior are present and independent of each other (aside from Finding 1's logic
  bug, not an independence bug).
- Scope: only task 1 touched; no new dependency; no schema change; no tests deleted; error
  style (`HTTPException` + short `detail`, 400/409) matches existing conventions.
- Pre-existing, unrelated observation (not introduced by this diff, not blocking): the three
  original tests (`test_shorten_and_redirect`, `test_rejects_bad_url`, `test_unknown_code_404`)
  still don't use the `temp_db` fixture and write to the real `links.db`, which
  `tests/AGENTS.md` now prohibits. Worth a follow-up cleanup, but out of scope for this change.
- `pytest`: 14 passed, 0 failed (1 unrelated `httpx`/`starlette` deprecation warning).

## Verdict to deliver to the user

```
REVISE — Implementation is correct and well-scoped, but the regression test for decision #3
(auto-generated code colliding with an existing alias) is vacuous: it claims alias "b" when
it needed to claim "c" (= encode(2), the id the next plain insert actually receives), so the
retry/suffix logic it's meant to guard is never exercised — reverting that logic would not
fail any test. Fix that one test (derive the colliding alias from the public API rather than
a hardcoded/assumed code, consistent with tests/AGENTS.md's "do not assume which code the next
POST /shorten returns"). Everything else — correctness, the other new tests, and scope — is
solid; all 14 tests currently pass.
```

No files were edited during this review.

