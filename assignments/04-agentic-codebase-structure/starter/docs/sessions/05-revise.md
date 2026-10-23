# Stage 4: Address the REVISE findings

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `acceptEdits`

## Prompt

```text
Address the review in docs/sessions/04-review.md. (1) Rewrite the auto-generated-code collision test so it really exercises the retry path, deriving the colliding code through the public API as the review suggests, and confirm it fails if the retry loop is removed. (2) Make the three original tests use the temporary database too, so no test writes to the real links.db, as tests/AGENTS.md requires. Do not change application behavior. Run pytest.
```

## Tool calls, in order

1. Read: `docs/sessions/04-review.md`
2. Read: `tests/test_main.py`
3. Read: `tests/AGENTS.md`
4. Read: `main.py`
5. Edit: `tests/test_main.py`
6. Edit: `tests/test_main.py`
7. Bash: `source .venv/bin/activate 2>/dev/null; python -m pytest -v 2>&1`
8. Bash: `ls -la | grep -i venv`
9. Bash: `./.venv/bin/python -m pytest -v 2>&1`
10. Bash: `./.venv/bin/python -m pytest -v`
11. Bash: `tests"`
12. Bash: `tests"`
13. Bash: `pwd`
14. Bash: `pytest -v`
15. Read: `main.py`
16. Edit: `main.py`
17. Bash: `pytest -v -k test_auto_generated_code_recovers_from_collision_with_claimed_alias`
18. Edit: `main.py`
19. Bash: `pytest -v && echo "---DIFF---" && git diff -- main.py tests/test_main.py`
20. Bash: `git status --short`

## Agent's final answer

Only `tests/test_main.py` is modified — `main.py` is back to its original state and `links.db` was not touched. Both review items are addressed:

1. **Collision test rewritten**: `test_auto_generated_code_recovers_from_collision_with_claimed_alias` now probes a throwaway db via the public API to learn the real next natural code (no hardcoded/assumed literal), then claims that exact value as an alias in a second fresh db before issuing a plain `POST /shorten`. I verified it empirically by temporarily reverting the retry/suffix loop in `main.py` to the original two-liner — the test failed with `sqlite3.IntegrityError` as expected — then restored the original logic (confirmed via `git diff`, no app changes survive).

2. **Original three tests** (`test_shorten_and_redirect`, `test_rejects_bad_url`, `test_unknown_code_404`) now take the `temp_db` fixture, so no test writes to the real `links.db`.

All 14 tests pass with `main.py` unchanged.
