---
name: implement-feature
description: Implement one feature task from docs/TASKS.md in the link shortener, test first. Use when asked to build a task such as a custom alias, a click counter, or link expiry.
argument-hint: "[task number or name]"
---

# Implement a feature task

Task to implement: $ARGUMENTS

Follow these steps in order. Do not skip ahead to writing application code.

1. **Read the task and the guidance.** Read the task in `docs/TASKS.md`, the root `AGENTS.md`,
   and `tests/AGENTS.md`. Implement only this task.
2. **Inspect the code and tests.** Read `main.py` and `tests/test_main.py`. Note how codes are
   generated and stored, and which routes could be affected.
3. **State the behavior and the files.** Before editing, write down:
   - the expected behavior, including every status code the task introduces,
   - the edge cases (invalid input, conflicts, interaction with existing codes and routes),
   - the files you expect to change.
4. **Add failing behavioral tests.** Add tests in `tests/` for the success case and each failure
   or edge case from step 3. Run them and confirm they fail for the expected reason, not
   because of an import error or a typo:

   ```bash
   pytest tests/test_main.py
   ```

5. **Implement the smallest change** in `main.py` that makes the tests pass. Do not refactor
   unrelated code or start another task.
6. **Run the whole suite** and fix any failure before continuing:

   ```bash
   pytest
   ```

7. **Summarize** in this shape:

   ```text
   Behavior: what changed for an API user
   Files: each file changed and why
   Tests: tests added, and the pytest result
   Remaining risks: anything not covered or decided
   ```
