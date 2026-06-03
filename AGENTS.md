# Agent Instructions (Reusable)

## Required Startup Context
1. Read `aidocs/KNOWLEDGE.md` before making plans or edits.
2. Treat `aidocs/KNOWLEDGE.md` as canonical current project context.
3. Treat `aidocs/CHANGES.md` as append-only change history that is read only on demand (for example when the user asks for history or when debugging historical drift).

## Update Policy
1. If you change architecture, schema, workflows, CLI behavior, dependencies, tests, or operational behavior, update `aidocs/KNOWLEDGE.md` in the same task.
2. Add an append-only entry to the bottom of `aidocs/CHANGES.md` for every completed change in the same task.
3. Keep both files factual and aligned with the observed repository state.
4. Maintain a dedicated section in `aidocs/KNOWLEDGE.md` for human-run operational scripts, listing each script and all supported CLI options; exclude one-time Codex-only migration utilities.
5. Treat `aidocs/KNOWLEDGE.md` as state-of-the-art runtime documentation only: always reflect what the system does now, and do not use it as a historical log.
6. Treat `aidocs/CHANGES.md` as an append-only log file, not required reading during normal work unless historical context is explicitly needed.
7. Supporting docs referenced from `aidocs/KNOWLEDGE.md` are on-demand for reading, but they are mandatory to update whenever a code change affects their area.
8. Update the specific supporting doc that matches the change domain:
   - `aidocs/data/data-model.md` for schema, table-role, or JSON-shape changes,
   - `aidocs/runtime/runtime-scripts.md` for active script behavior or CLI changes,
   - `aidocs/ai/ai-and-translation.md` for AI model, prompt, pricing, or translation-flow changes,
   - `aidocs/runtime/dev-workflows.md` for local debugging, temp-dir, Docker, or developer workflow changes.


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
