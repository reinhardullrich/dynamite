# Full Audit

Audit date: 2026-06-04
Repository: `/home/reinhard/projects/thomas/dynamite`
Branch/worktree audited: `Fortran-cleanup`.

This folder is the current full local audit package for the personal DYNAMITE
fork. It intentionally lives under `aidocs/`, not upstream `docs/`.

## Current Baseline

This audit treats the current working tree as the source of truth. The files
in this folder are current-open-finding documents.

- Active orbit-library generation uses the direct shared-library API in
  `dynamite/orblib_api.py`.
- The active Fortran build product is
  `orblib_fortran/build/lib/liborblib_fortran.so`.
- Current pytest coverage lives under `tests/`.

## Verification Run

Commands run on 2026-06-04:

```bash
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q dynamite tests
make -C orblib_fortran shared
git diff --check
.venv/bin/python -m pytest
DYNAMITE_RUN_SLOW_TESTS=1 DYNAMITE_RUN_ORBLIB_FORTRAN_TESTS=1 .venv/bin/python -m pytest tests/test_fortran_orblib_output.py tests/test_fortran_inventory.py
```

Results:

- `pip check`: passed, with the local pip-cache ownership warning.
- Python compile check: passed.
- Fortran shared-library build: passed.
- `git diff --check`: passed.
- Default pytest: 62 passed, 6 skipped, 1 warning.
- Opt-in slow Fortran/output tests: 11 passed, 1 warning.

The warning is the existing VorBin deprecation warning emitted by
`dynamite/coloring.py`.

## Files

- `SUMMARY.md`: prioritized current audit summary.
- `AUDIT_PLAN.md`: scope and review method.
- `00_environment.md`: local environment and verification baseline.
- `01_build_packaging.md`: package, build, CI, dependency risks.
- `02_configuration_runtime.md`: configuration, destructive operations,
  validation, logging.
- `03_physical_model_parameter_space.md`: physical parameters and generators.
- `04_data_ingestion.md`: MGE, kinematics, populations, and data-prep inputs.
- `05_model_state_iteration.md`: `all_models.ecsv`, model directories, resume,
  pruning, external chi-square.
- `06_orbit_library_boundary.md`: direct Fortran shared-library API, orbit
  readers, qgrid/LOSVD outputs.
- `07_weight_solving.md`: active Python NNLS and CVXOPT option.
- `08_fortran_backend.md`: active Fortran backend risks.
- `09_analysis_plotting_coloring.md`: analysis, plotting, and coloring risks.
- `10_tests_examples_docs.md`: tests, examples, docs, and CI coverage.
- `11_scientific_numerical_correctness.md`: cross-cutting scientific risks.
- `12_operational_risk.md`: reproducibility, destructive writes, concurrency,
  local/global install boundaries.
- `13_active_runtime_verification.md`: current acceptance/verification policy.
- `14_improvement_opportunities.md`: still-current improvement roadmap.
- `15_active_nnls_solver_benchmark.md`: current NNLS policy and benchmark plan.

## How To Read

Start with `SUMMARY.md`. Then read the topic file for the subsystem you are
about to modify. Findings in this folder should be treated as currently open
unless the code has changed after this audit date.
