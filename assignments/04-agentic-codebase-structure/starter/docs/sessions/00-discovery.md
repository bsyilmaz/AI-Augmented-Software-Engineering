# Stage 0: What the agent loads before reading any file

- **Agent:** Claude Code (`claude-sonnet-5`), headless `claude -p` from `starter/`
- **Permission mode:** `plan`

## Prompt

```text
Before reading any file: list every project instruction file that is already loaded into your context (give its path relative to this directory), say whether tests/AGENTS.md is loaded yet, and list the project skills you can invoke. Do not read or edit files.
```

## Tool calls, in order

(none)

## Agent's final answer

Here's what's currently loaded, without reading or editing anything:

**Project instruction files loaded into context:**
- `AGENTS.md` (this directory: `~/Desktop/ÖDEVDOSYAM2027/AI-Augmented-Software-Engineering/assignments/04-agentic-codebase-structure/starter/AGENTS.md`)

**Is `tests/AGENTS.md` loaded?**
No. Per the root `AGENTS.md`, that file "loads when you work in `tests/`" — it hasn't been pulled in yet since I haven't touched anything under `tests/`.

**Project skills I can invoke:**
- `implement-feature` — "Implement one feature task from docs/TASKS.md in the link shortener, test first." (this is the only skill scoped to this project, per `.claude/skills/implement-feature/` referenced in `AGENTS.md`)

(All other skills visible to me — vercel:*, anthropic-skills:*, code-review, simplify, etc. — are global/environment skills, not specific to this link-shortener project.)
