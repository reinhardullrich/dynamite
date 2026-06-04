# Full Audit Plan

Audit date: 2026-06-04

## Scope

Check the full local DYNAMITE fork at the current repository state. Treat the
current repository state as authoritative.

## Rules

- Audit `dynamite/`, `orblib_fortran/`, `tests/`, `.github/`, `archive/`, and
  `aidocs/`.
- Do not treat `archive/`, `orblib_fortran/unused/`, generated caches, build
  products, or dev-test scripts as active runtime code unless current source uses
  them.
- Keep local audit notes in `aidocs/`.
- Do not modify upstream Sphinx `docs/` for this audit.
- Delete stale findings instead of keeping them as history.
- Keep open findings with current evidence.

## Review Split

1. Environment and verification baseline.
2. Build, packaging, and CI.
3. Configuration and runtime bootstrap.
4. Physical model and parameter space.
5. Data ingestion and external input validation.
6. Model state, iteration, and output mutation.
7. Orbit-library Python/Fortran boundary.
8. Weight solving and optimization.
9. Active Fortran backend.
10. Analysis, plotting, and coloring.
11. Tests, examples, notebooks, docs.
12. Scientific/numerical correctness.
13. Operational risk.
14. Improvement opportunities.
15. Active NNLS policy and benchmark plan.

## Verification Commands

```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q dynamite tests
make -C orblib_fortran shared
git diff --check
.venv/bin/python -m pytest
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py tests/test_fortran_inventory.py
```
