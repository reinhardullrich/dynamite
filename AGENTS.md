# Agent Instructions (Project Local)

## Project Context
1. Read `aidocs/KNOWLEDGE.md` when starting work in this repo.
2. Treat `aidocs/KNOWLEDGE.md` as current project context.
3. Read `aidocs/CHANGES.md` only when project instructions require history, when debugging historical drift, or when the user asks for history.

## Documentation Notes
1. Keep `aidocs/KNOWLEDGE.md` factual and current.
2. When a change affects architecture, schema, workflows, command-line interface behavior, dependencies, tests, operational behavior, or human-run scripts, update `aidocs/KNOWLEDGE.md` or the specific supporting doc affected by the change.
3. Do not add `aidocs/CHANGES.md` entries automatically for every task. Update it only when a human-readable historical log is useful for the change.
4. Maintain human-run operational script documentation when active script behavior or command-line options change.

## Local Host Browser Automation Tools
1. Host-side Playwright and Browser Use are installed in:
   - `~/tools/browser-automation`
2. The host virtualenv is:
   - `~/tools/browser-automation/.venv`
3. Use this toolchain when a task benefits from direct host browser automation rather than Docker-contained browser execution.
4. This location may be used for:
   - temporary Playwright-driven inspection/debug sessions,
   - Browser Use exploratory browsing tasks,
   - logged-in website/admin-console inspection where the host browser session is more practical.
5. Prefer temporary inline commands over adding throwaway repo scripts when this host toolchain is sufficient for the task.
