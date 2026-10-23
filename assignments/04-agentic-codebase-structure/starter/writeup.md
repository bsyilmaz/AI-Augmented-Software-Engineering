# Week 4 Writeup: An Agent-Ready Link Shortener

**Agent:** Claude Code 2.1.303 (`claude-sonnet-5`). **Task:** 1, custom alias. **Result:** 14
tests pass. Each stage is recorded in [`docs/sessions/`](docs/sessions/).

## 1. What is in `AGENTS.md`, and why is it broadly available?

[`AGENTS.md`](AGENTS.md) (52 lines) has the file map, install/run/test commands, product
boundaries, how codes work, and the understand → test → implement → verify workflow. Every task
needs this, so it loads in every session. It also notes that the `GET /{code}` catch-all shares
URL space with `/docs` and `/openapi.json`.

## 2. What instruction is scoped, and when does it load?

[`tests/AGENTS.md`](tests/AGENTS.md): test through `TestClient`, cover success and failure, use a
temporary database, and assert behavior, not internals. I moved the tests into `tests/` so the rule
has a folder to scope to. Application-only or documentation work does not need it.

## 3. What procedure does the workflow encode?

[`.claude/skills/implement-feature/SKILL.md`](.claude/skills/implement-feature/SKILL.md): read the
task and guidance, inspect code and tests, state behavior, edge cases, and files, add failing
tests, make the smallest change, run `pytest`, and summarize remaining risks.

## 4. How does Claude Code discover each artifact?

- **`AGENTS.md`:** read at session start when no `CLAUDE.md` exists here or above.
- **`tests/AGENTS.md`:** loaded when Claude reads a file in `tests/`.
  [00-discovery](docs/sessions/00-discovery.md) shows the root file loaded and this one not yet.
- **Skill:** read from `.claude/skills/<name>/SKILL.md`; Claude Code ignores `.agents/`. I ran it
  as `/implement-feature 1`.

## 5. What did planning and review catch?

- **Plan** ([01](docs/sessions/01-plan.md)) flagged that an auto-generated code could hit an
  existing alias (a 500) and that aliases like `docs` are unreachable, but left both out. I chose
  to fix both ([02](docs/sessions/02-plan-decisions.md)).
- **Review** ([04](docs/sessions/04-review.md)) returned **REVISE**: the collision test never
  collided, because the alias insert used up the row id. The fix derives the code through the API
  ([05](docs/sessions/05-revise.md)); removing the retry loop now fails the test.
- **Re-review** ([06](docs/sessions/06-re-review.md)) returned **ACCEPT**.

Remaining risks I found: aliases containing `?` or `#` are accepted but unreachable, and
importing `main.py` still creates an empty `links.db`.

## 6. What I learned

What surprised me most was that one test passed along with all the others without really testing anything, and that the second review did not catch the `?` and `#` problem. The repository structure did help: `AGENTS.md` told the agent the project boundaries, the files, and the workflow, and the skill supported a test-first approach. But the agent broke a rule from `tests/AGENTS.md` in its first test even though it had read it, so instructions alone were not enough. Next time I would use more mutation testing to confirm that tests fail when they should, test edge cases such as URLs and aliases more thoroughly, and make sure agents can reach important instructions at the right time.
