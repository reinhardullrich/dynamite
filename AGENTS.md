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

## Documentation Boundaries
1. Keep this file generic and reusable across repositories.
2. Store project-specific details only in `aidocs/KNOWLEDGE.md`.
3. Store historical change notes only in `aidocs/CHANGES.md`.
4. Exception for this local workspace: store user machine hardware/OS profile in `AGENTS.md` (not `aidocs/KNOWLEDGE.md`), because it applies across projects on this computer.

## Local Workspace Runtime Startup Rule
1. `db-init` must do nothing to the database on normal startup.
2. Normal container startup must not run schema-init, backfills, rebuilds, repairs, or any other DB-mutating step automatically.
3. `db-init` may exist only as a no-op dependency gate so other services can wait for startup ordering.
4. Any DB mutation must be an explicit human-approved action, not part of ordinary stack startup.
5. As long as there is no real split between test and production, the database is copied as-is and startup must treat it as already migrated.

## Local Workspace Escalation Rule
1. Always try the non-escalated version of a command first.
2. Only escalate after the non-escalated command actually fails or is clearly blocked by sandboxing/permissions.
3. Do not pre-emptively escalate just because a similar command failed earlier in the session.
4. Current user note: after a CLI restart, retry the normal non-escalated path first because earlier escalation-related failures may no longer apply.
5. Do not run `sudo` from Codex. If a task needs root privileges, provide the exact command for the user to execute manually, then continue after the user reports the result.

## Context Compaction Policy (Local Workspace)
1. Current workspace preference: use aggressive context compaction.
2. Target after compaction: recover enough context to leave at least `45%` of the total context window free; prefer `50%` to `60%` free when possible.
3. Compact summaries should keep only:
   - active rules and constraints,
   - current architecture and current file locations,
   - pending work and unresolved blockers,
   - only the minimum recent results needed for the next step.
4. Compact summaries should aggressively drop:
   - resolved historical debugging chains,
   - old run/session identifiers,
   - large file inventories unless they are directly needed,
   - repeated documentation-policy restatements,
   - examples and explanations that are not needed for the next action.
5. Compact summaries must not restate `AGENTS.md` / `aidocs/KNOWLEDGE.md` policy unless that policy changed in the recent work.
6. Compact summaries should prefer short bullet lists over prose and should stay close to the minimum needed to resume work.
7. Do not compact again just because time passed; compact again only when substantial new state was created after the last compaction or when context pressure is high again.
8. This is a local working preference, not a permanent global rule. Revert it explicitly if a less aggressive compaction style is wanted later.

## Fallback Policy
1. Do not add implicit or automatic fallbacks unless the user explicitly asked for that fallback behavior.
2. Prefer a hard error over silent degradation when a required path, provider, request mode, or data source fails.
3. If a fallback is intentionally added, make it explicit in code and document it in `aidocs/KNOWLEDGE.md`.
4. Do not substitute a different transport or execution path (for example `requests` instead of Playwright) unless the user explicitly approved that fallback.

## Wrapper Function Policy
1. Prefer direct calls over helper wrappers.
2. Do not create semantic-alias functions unless they reduce complexity at multiple call sites.
3. If a wrapper would have the same parameters and the same return value as the wrapped function, do not create it.
4. Only introduce a wrapper when it adds real value such as validation, transformation, caching, policy centralization, abstraction over genuinely interchangeable implementations, or explicit error handling.

## Scraper Duplication Policy
1. Before adding new scraper logic, search for an existing function or module that already does the same website interaction.
2. If equivalent logic already exists, reuse it or extract it into shared code instead of copying it.
3. Do not duplicate provider-page interaction code across scrapers unless the behavior is genuinely different.
4. When the same site interaction appears in a second active codepath, stop and refactor it into a shared helper or module first.
5. Prefer one shared implementation with configurable timing or options over two near-identical implementations.
6. Treat duplicated active logic as a bug, not as acceptable convenience.
7. When doing review or cleanup work, prioritize:
   - duplicated active logic,
   - dead code,
   - pass-through wrappers,
   - parallel helper stacks for the same workflow.

## Hardware Context Handling
1. If the user provides machine or environment constraints (CPU/GPU/RAM/OS), record them in `AGENTS.md` for this workspace.
2. Treat that hardware profile as an optimization baseline for implementation choices and performance guidance.
3. Keep hardware assumptions explicit and update them when new verified information is provided.

## Local Machine Hardware Profile (User Exception)
1. Device: TUXEDO Pulse 15 Gen1.
2. OS: TUXEDO OS 24.04 family (local kernel observed: `6.14.0-123037-tuxedo`).
3. CPU: AMD Ryzen 7 4800H (8 cores / 16 threads).
4. GPU: AMD Renoir integrated graphics (`Radeon Vega Series / Radeon Vega Mobile Series`).
5. RAM: 64 GB class; RAM is usually not a primary bottleneck.
6. Practical baseline:
   - optimize for CPU throughput/latency first,
   - treat iGPU acceleration as optional and backend-dependent,
   - do not over-optimize for RAM conservation unless explicitly requested.

Reference links used for hardware summary:
- https://www.tuxedocomputers.com/en/Linux-Hardware/Linux-Notebooks/15-16-inch/TUXEDO-Pulse-15-Gen1.tuxedo
- https://docs.mesa3d.org/drivers/radv.html

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
