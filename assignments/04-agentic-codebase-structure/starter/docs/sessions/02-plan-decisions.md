# Human decisions on the plan

The plan in `01-plan.md` asked two questions and flagged two risks it chose not to fix. My answers:

1. **Empty or whitespace-only alias:** reject with 400, as the plan recommended. An empty code can
   never be reached by `GET /{code}`.
2. **Strip the alias?** No. Store it exactly as given, as the plan recommended.
3. **A future auto-generated code colliding with an existing alias:** fix it in this task. The plan
   flagged it but left it out under "smallest change". The collision is created by this task and
   would return a 500 from a plain `POST /shorten` with no alias, so it is part of the task.
4. **Aliases that can never be reached:** reject them with 400. That covers aliases containing `/`
   and aliases that collide with routes FastAPI already serves (`docs`, `redoc`, `openapi.json`).
   The plan listed these as pre-existing limitations, but accepting such an alias returns a short
   URL that does not work.
