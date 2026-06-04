# 10 Tests, Examples, CI, and Upstream Docs Audit

Audit date: 2026-06-04

## Current Test State

Active tests are under `tests/`.

Verification results:

- default pytest: 62 passed, 6 skipped;
- opt-in Fortran/output tests: 11 passed.

## Findings

### TED-001 - Example/dev-test information is only partially covered by active pytest

Severity: Medium.

- not every notebook/dev script has an active pytest equivalent;
- data-prep and plotting workflows remain under-covered.

Recommendation: extract additional fixtures only when those workflows are
actively supported.

### TED-002 - Upstream Sphinx docs are not aligned with local runtime direction

This audit follows the local documentation boundary: AI/local audit docs live
under `aidocs/`; upstream user docs under `docs/` were not modified.

Recommendation: update upstream docs only when a user-facing feature or command
changes, not for local audit notes.

### TED-003 - Upstream docs still need alignment with active shared-library backend

Severity: Medium.

Local `aidocs/` and `tests/README.md` describe the current local state. Some
upstream docs still describe inactive workflows.

Recommendation: after code direction stabilizes, derive human-facing docs from
`aidocs/`.
